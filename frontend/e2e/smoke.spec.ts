import { test, expect } from '@playwright/test';

test('app shell loads and nav is visible', async ({ page }) => {
  await page.goto('/');

  // Should redirect to /console
  await expect(page).toHaveURL(/\/console$/);

  // Navigation bar should be visible
  await expect(page.getByRole('banner')).toBeVisible();

  // All three nav links should be present
  await expect(page.getByRole('link', { name: 'Console' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ops' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Portal' })).toBeVisible();

  // Console heading should be visible
  await expect(
    page.getByRole('heading', { name: 'Processing-Agent Console' }),
  ).toBeVisible();
});
