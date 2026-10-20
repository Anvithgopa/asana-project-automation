/**
 * Asana Dependency Cascade & Dynamic Timeline Scheduler
 * 
 * Automatically propagates date shifts across dependent tasks using
 * Directed Acyclic Graph (DAG) traversal, respecting working day calendars,
 * dependency types (FS, SS, FF, SF), lag times, and constraint flags.
 */

try {
  require('dotenv').config();
} catch (e) {}

let asana;
try {
  asana = require('asana');
} catch (e) {}

// Initialize Asana API Client
const ACCESS_TOKEN = process.env.ASANA_ACCESS_TOKEN;
if (!ACCESS_TOKEN && process.env.NODE_ENV !== 'test') {
  console.warn('⚠️ Warning: ASANA_ACCESS_TOKEN is not set in environment or .env file.');
}

const client = ACCESS_TOKEN ? asana.Client.create().useAccessToken(ACCESS_TOKEN) : null;
const tasksApiInstance = client ? client.tasks : null;

const formatDate = date => {
  if (!date) return null;
  const d = typeof date === "string" ? new Date(date) : date;
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

function normalizeDate(date) {
  const d = new Date(date);
  d.setHours(0, 0, 0, 0);
  return d;
}

/**
 * Adds working days to a date, skipping weekends (Saturday & Sunday).
 */
function addWorkingDays(startDate, days) {
  if (isNaN(days) || days <= 0) return normalizeDate(startDate);
  let count = 0;
  const result = normalizeDate(startDate);
  while (count < days) {
    result.setDate(result.getDate() + 1);
    if (result.getDay() !== 0 && result.getDay() !== 6) {
      count++;
    }
  }
  return result;
}

/**
 * Adds or subtracts working days incorporating positive or negative lag time.
 */
function addWorkingDaysWithLag(startDate, lag) {
  const result = new Date(startDate);
  let moved = 0;

  if (lag === 0) return result;

  if (lag > 0) {
    while (moved < lag) {
      result.setDate(result.getDate() + 1);
      if (result.getDay() !== 0 && result.getDay() !== 6) {
        moved++;
      }
    }
  } else {
    while (moved > lag) {
      result.setDate(result.getDate() - 1);
      if (result.getDay() !== 0 && result.getDay() !== 6) {
        moved--;
      }
    }
  }
  return result;
}

/**
 * Subtracts working days from a date, skipping weekends.
 */
function subtractWorkingDays(endDate, days) {
  if (isNaN(days) || days <= 0) return normalizeDate(endDate);
  let count = 0;
  const result = normalizeDate(endDate);
  while (count < days) {
    result.setDate(result.getDate() - 1);
    if (result.getDay() !== 0 && result.getDay() !== 6) {
      count++;
    }
  }
  return result;
}

/**
 * Recursively cascades schedule changes to all dependent tasks in the DAG.
 */
async function updateDependentsRecursive(task, opts, visited = new Set()) {
  const taskGid = task.data?.gid || task.gid;
  const taskName = task.data?.name || task.name;

  if (visited.has(taskGid)) {
    console.log(`[DAG] Task already processed: ${taskName} (${taskGid})`);
    return;
  }
  visited.add(taskGid);

  const parentStart = task.data?.start_on ? new Date(task.data.start_on) : null;
  const parentDue = task.data?.due_on ? new Date(task.data.due_on) : null;

  for (const dep of (task.data?.dependents || [])) {
    if (!tasksApiInstance) {
      console.log(`[Simulation] Skipping remote fetch for dependent: ${dep.gid}`);
      continue;
    }

    let depTask = await tasksApiInstance.getTask(dep.gid, opts);
    const customFields = depTask.data?.custom_fields || [];

    const blockField = customFields.find(f => f.name === "Block");
    const blockValue = blockField?.enum_value?.name || null;

    const constraintField = customFields.find(f => f.name === "Constraint");
    const constraintFieldName = constraintField?.enum_value?.name;

    // Honor constraint locking
    if (["Yes", "Actual Start Date", "Actual Due Date", "Actual Start and Due Date", "HALT"].includes(constraintFieldName)) {
      console.log(`[Constraint Locked] Skipping schedule recalculation for ${depTask.data.name}`);
      continue;
    }

    let duration = null;
    const durationField = customFields.find(f => f.name === "Duration");
    const lagField = customFields.find(f => f.name === "Lag Time");
    let lagTime = lagField?.display_value ? parseInt(lagField.display_value, 10) : 0;

    if (durationField) {
      const raw = durationField.display_value || durationField.text_value || null;
      if (raw) {
        const match = String(raw).match(/\d+/);
        if (match) duration = parseInt(match[0], 10);
      }
    }

    if (!duration || !blockValue) continue;

    let newStart = null;
    let newDue = null;

    // Calculate dates based on Dependency Relationship
    if (blockValue === 'FS' && parentDue) {
      // Finish-to-Start: Dependent starts after parent finishes
      newStart = addWorkingDays(parentDue, 1);
      if (lagTime !== 0) {
        newStart = addWorkingDaysWithLag(parentDue, lagTime || 1);
      }
      newDue = addWorkingDays(newStart, duration - 1);
    } else if (blockValue === 'FF' && parentDue) {
      // Finish-to-Finish: Dependent finishes with parent
      newDue = new Date(parentDue);
      newStart = subtractWorkingDays(newDue, duration - 1);
    } else if (blockValue === 'SS' && parentStart) {
      // Start-to-Start: Dependent starts with parent
      newStart = new Date(parentStart);
      newDue = addWorkingDays(newStart, duration - 1);
    } else if (blockValue === 'SF' && parentStart) {
      // Start-to-Finish: Dependent finishes after parent starts
      newDue = new Date(parentStart);
      newStart = subtractWorkingDays(newDue, duration - 1);
    }

    if (newStart && newDue) {
      console.log(`[Update] ${depTask.data.name}: ${formatDate(newStart)} -> ${formatDate(newDue)}`);
      await tasksApiInstance.updateTask(
        { data: { start_on: formatDate(newStart), due_on: formatDate(newDue) } },
        depTask.data.gid,
        opts
      );
      depTask = await tasksApiInstance.getTask(dep.gid, opts);
    }

    // Recurse down the dependent branch
    await updateDependentsRecursive(depTask, opts, visited);
  }
}

/**
 * Main execution entry point for updating a task schedule and rolling up to parent.
 */
async function cascadeSchedule(taskGid) {
  if (!tasksApiInstance) {
    throw new Error('Asana API client is not initialized. Please set ASANA_ACCESS_TOKEN.');
  }

  const opts = {
    opt_fields: "actual_time_minutes,approval_status,assignee,assignee.name,assignee_status,completed,completed_at,created_at,custom_fields,custom_fields.display_value,custom_fields.enum_value.name,custom_fields.name,dependencies,dependents,due_on,start_on,name,parent,parent.gid,parent.name"
  };

  console.log(`[Start] Fetching root task: ${taskGid}`);
  const task = await tasksApiInstance.getTask(taskGid, opts);

  // Cascade downstream
  await updateDependentsRecursive(task, opts);

  // Update parent task date bounds (Rollup)
  const parentGid = task.data.parent?.gid;
  if (parentGid) {
    const subtasks = await tasksApiInstance.getSubtasksForTask(parentGid);
    const subtaskDates = [];

    for (const sub of subtasks.data) {
      const subtaskDetail = await tasksApiInstance.getTask(sub.gid, opts);
      const start = subtaskDetail.data.start_on;
      const due = subtaskDetail.data.due_on;
      if (start || due) {
        subtaskDates.push({ start, due });
      }
    }

    const validStartDates = subtaskDates.map(d => d.start).filter(Boolean);
    const validDueDates = subtaskDates.map(d => d.due).filter(Boolean);

    const earliestStart = validStartDates.length > 0
      ? validStartDates.reduce((min, d) => (d < min ? d : min))
      : null;
    const latestDue = validDueDates.length > 0
      ? validDueDates.reduce((max, d) => (d > max ? d : max))
      : null;

    const updateData = {};
    if (earliestStart) updateData.start_on = formatDate(earliestStart);
    if (latestDue) updateData.due_on = formatDate(latestDue);

    if (Object.keys(updateData).length > 0) {
      console.log(`[Parent Rollup] Updating parent task ${parentGid} with span ${updateData.start_on} -> ${updateData.due_on}`);
      await tasksApiInstance.updateTask({ data: updateData }, parentGid);
    }
  }

  console.log('[Done] Dependency cascade completed successfully.');
}

module.exports = {
  formatDate,
  normalizeDate,
  addWorkingDays,
  addWorkingDaysWithLag,
  subtractWorkingDays,
  updateDependentsRecursive,
  cascadeSchedule
};

if (require.main === module) {
  const targetGid = process.argv[2] || process.env.TARGET_TASK_GID;
  if (!targetGid) {
    console.error('Usage: node dependency_scheduler.js <TASK_GID>');
    process.exit(1);
  }
  cascadeSchedule(targetGid).catch(err => {
    console.error('Scheduling error:', err);
    process.exit(1);
  });
}
