import { test, expect } from '@playwright/test';
test('two-question form displays discovery and real configuration failure', async ({page}) => {
  await page.route('**/api/analyze', route => {
    const body = route.request().postDataJSON();
    expect(body).toEqual({dataset_interest: 'Test records', question: 'Count test records in 2025'});
    return route.fulfill({contentType: 'application/x-ndjson', body: [
      {type: 'progress', message: 'Searching…'},
      {type: 'datasets', datasets: [{dataset_id: 'abcd-1234', title: 'Synthetic browser fixture', description: 'Test only'}]},
      {type: 'error', message: 'AI analysis is not configured.'},
    ].map(e => JSON.stringify(e)).join('\n') + '\n'});
  });
  await page.goto('/');
  await page.getByLabel('What data are you interested in?').fill('Test records');
  await page.getByLabel('What do you want to learn from it?').fill('Count test records in 2025');
  await page.getByRole('button', {name: 'Explore the data'}).click();
  await expect(page.getByRole('alert', {name: 'Couldn’t complete the analysis'})).toContainText('AI analysis is not configured.');
  await expect(page.getByText('Synthetic browser fixture')).toBeVisible();
  await expect(page.getByRole('button', {name: 'Explore the data'})).toBeEnabled();
});

test('renders actual returned table and chart with source and time', async ({page}) => {
  await page.route('**/api/analyze', route => route.fulfill({contentType: 'application/x-ndjson', body: [
    {type: 'result', result: {dataset_id: 'abcd-1234', title: 'Synthetic fixture',
      rows: [{period: '2025-01-01', value: '3'}, {period: '2025-02-01', value: '4'}],
      query: {time_bucket: {interval: 'month'}}, parameters: {}, warnings: ['Counts are rows.'],
      truncated: false, source_url: 'https://data.seattle.gov/d/abcd-1234', retrieved_at: '2026-01-01T00:00:00Z'}},
    {type: 'answer', status: 'answered', message: 'Synthetic result for browser test only.'},
  ].map(e => JSON.stringify(e)).join('\n')}));
  await page.goto('/');
  await page.getByLabel('What data are you interested in?').fill('Test records');
  await page.getByLabel('What do you want to learn from it?').fill('Show a test trend');
  await page.getByRole('button', {name: 'Explore the data'}).click();
  await expect(page.getByRole('table')).toBeVisible();
  await expect(page.getByRole('img', {name: /2025-01-01: 3/})).toBeVisible();
  await expect(page.getByRole('link', {name: 'View official source'})).toHaveAttribute('href', 'https://data.seattle.gov/d/abcd-1234');
  await expect(page.getByText('Counts are rows.')).toBeVisible();
});

test('disconnected stream is an error instead of a successful empty answer', async ({page}) => {
  await page.route('**/api/analyze', route => route.fulfill({contentType: 'application/x-ndjson', body: '{"type":"progress","message":"Searching"}\n'}));
  await page.goto('/');
  await page.getByLabel('What data are you interested in?').fill('Test records');
  await page.getByLabel('What do you want to learn from it?').fill('Show a test trend');
  await page.getByRole('button', {name: 'Explore the data'}).click();
  await expect(page.getByRole('alert', {name: 'Couldn’t complete the analysis'})).toContainText('connection ended');
});
