import { test, expect } from '@playwright/test';

test('app shell loads and the surface nav is visible', async ({ page }) => {
  await page.goto('/');

  // The default route redirects to the Split-Screen Theater.
  await expect(page).toHaveURL(/\/theater$/);

  // Navigation bar is visible with all surface links.
  await expect(page.getByRole('banner')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Console' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ops' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Portal' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Time-warp' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Timeline' })).toBeVisible();

  // The theater renders both zones with the Gateway boundary between them.
  await expect(page.getByTestId('external-zone')).toBeVisible();
  await expect(page.getByTestId('internal-zone')).toBeVisible();
});
