import { test, expect } from '@playwright/test'

test('home redirects to chat page', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/chat/)
  await expect(page.getByRole('heading', { name: 'Lyubava' })).toBeVisible()
})

test('navigation opens admin page', async ({ page }) => {
  await page.goto('/chat')
  await page.getByRole('link', { name: 'Админ' }).click()
  await expect(page).toHaveURL(/\/admin/)
  await expect(page.getByRole('heading', { name: 'Админ' })).toBeVisible()
  await expect(page.getByText('accuracy: —')).toBeVisible()
})

test('chat input is available on chat page', async ({ page }) => {
  await page.goto('/chat')
  await expect(page.getByRole('textbox')).toBeVisible()
})
