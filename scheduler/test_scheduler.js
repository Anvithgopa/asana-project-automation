/**
 * Unit Test & Simulation Suite for Dependency Scheduler
 * Tests working day calculations, weekend skipping, and lag time logic.
 */

const {
  formatDate,
  addWorkingDays,
  addWorkingDaysWithLag,
  subtractWorkingDays
} = require('./dependency_scheduler');

function assert(condition, message) {
  if (!condition) {
    console.error(`❌ FAILED: ${message}`);
    process.exit(1);
  }
  console.log(`✅ PASSED: ${message}`);
}

console.log('--- Testing Date & Working Days Engine ---');

// Friday Nov 6, 2026
const friday = new Date('2026-11-06T00:00:00');

// 1 working day after Friday should be Monday Nov 9 (skipping Sat & Sun)
const nextWorkingDay = addWorkingDays(friday, 1);
assert(formatDate(nextWorkingDay) === '2026-11-09', 'Friday + 1 working day is Monday (skips weekend)');

// 5 working days after Friday Nov 6 should be Friday Nov 13
const fiveWorkingDays = addWorkingDays(friday, 5);
assert(formatDate(fiveWorkingDays) === '2026-11-13', 'Friday + 5 working days is next Friday');

// Monday Nov 9 - 1 working day should be Friday Nov 6
const monday = new Date('2026-11-09T00:00:00');
const prevWorkingDay = subtractWorkingDays(monday, 1);
assert(formatDate(prevWorkingDay) === '2026-11-06', 'Monday - 1 working day is Friday (skips weekend)');

// Testing Lag Time: Friday + 2 days lag
const lagTest = addWorkingDaysWithLag(friday, 2);
assert(formatDate(lagTest) === '2026-11-10', 'Friday + 2 lag days is Tuesday');

console.log('--- All Date Calculation Tests Passed Successfully! ---');
