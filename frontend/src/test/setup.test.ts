import { getConfig } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

const TESTING_LIBRARY_DEFAULT_WAIT_MS: number = 1000;

describe('test setup', () => {
  it('waits longer than the Testing Library default, below the time limit of a test', ({
    task,
  }) => {
    const asyncWaitMs: number = getConfig().asyncUtilTimeout;

    expect(asyncWaitMs).toBeGreaterThan(TESTING_LIBRARY_DEFAULT_WAIT_MS);
    expect(asyncWaitMs).toBeLessThan(task.timeout);
  });
});
