import { expect, test } from '@playwright/test'

function unique(value: string): string {
  return `${value}-${Date.now()}`
}

test('mini-CRM flow to quote linkage', async ({ page, request }) => {
  const tenantId = crypto.randomUUID()
  const accountName = unique('PW Account')
  const contactEmail = `pw-contact-${Date.now()}@example.com`
  const opportunityName = unique('PW Opportunity')
  const catalogCode = unique('PW-SKU')
  const catalogName = unique('PW Product')

  await page.goto('/')

  await page.getByLabel('Work Email').fill('admin@spt.com')
  await page.getByLabel('Password').fill('r@ndom11')
  await page.getByLabel('Tenant ID').fill(tenantId)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page.getByRole('heading', { name: 'Admin Workspace' })).toBeVisible()

  await page.getByRole('button', { name: /Accounts/ }).first().click()
  await page.getByPlaceholder('Account name (required)').fill(accountName)
  await page.getByPlaceholder('External ID (optional)').fill(unique('PW-EXT'))
  await page.getByPlaceholder('Segment (SMB / Mid-Market / Enterprise)').fill('ENTERPRISE')
  await page.getByPlaceholder('Industry (Healthcare, Finance...)').fill('TECHNOLOGY')
  await page.getByPlaceholder('Account owner').fill('Playwright Owner')
  await page.getByPlaceholder('Website URL').fill('https://example.com')
  await page.getByRole('button', { name: 'Create Account' }).click()
  await expect(page.getByText('Account created')).toBeVisible()
  await expect(page.getByText(accountName)).toBeVisible()

  await page.getByRole('button', { name: /Contacts/ }).first().click()
  await page.getByRole('combobox').first().selectOption({ label: accountName })
  await page.getByPlaceholder('Contact name').first().fill('Playwright Contact')
  await page.getByPlaceholder('Email (required)').fill(contactEmail)
  await page.getByPlaceholder('Phone').first().fill('+1-555-0101')
  await page.getByPlaceholder('Title').first().fill('Procurement Manager')
  await page.getByPlaceholder('Role (Decision Maker / Finance / Legal...)').fill('DECISION_MAKER')
  await page.getByRole('button', { name: 'Save Contact' }).click()
  await expect(page.getByText('Contact saved')).toBeVisible()
  await expect(page.getByText(contactEmail)).toBeVisible()

  await page.getByRole('button', { name: /Leads & Opportunities/ }).first().click()
  await page.getByRole('combobox').first().selectOption({ label: accountName })
  await page.getByRole('combobox').nth(1).selectOption('OPPORTUNITY')
  await page.getByPlaceholder('Lead / Opportunity name').first().fill(opportunityName)
  await page.getByRole('spinbutton').first().fill('250000')
  await page.getByRole('spinbutton').nth(1).fill('40')
  await page.getByRole('button', { name: 'Save Lead / Opportunity' }).click()
  await expect(page.getByText('Lead/Opportunity created')).toBeVisible()
  await expect(page.getByText(opportunityName)).toBeVisible()

  await page.getByRole('button', { name: /Pricing Simulator/ }).first().click()
  await page.getByRole('button', { name: 'Create + Publish' }).click()
  await expect(page.getByText(/created and published/i)).toBeVisible()

  const tokenResp = await request.post('http://127.0.0.1:8000/api/auth/dev-token', {
    data: { tenant_id: tenantId, email: 'admin@spt.com', password: 'r@ndom11' },
  })
  expect(tokenResp.ok()).toBeTruthy()
  const { access_token: accessToken } = (await tokenResp.json()) as { access_token: string }
  const authHeaders = {
    'X-Tenant-Id': tenantId,
    Authorization: `Bearer ${accessToken}`,
  }

  const customersResp = await request.get('http://127.0.0.1:8000/api/guided-quotes/customers?search=' + encodeURIComponent(accountName), {
    headers: authHeaders,
  })
  expect(customersResp.ok()).toBeTruthy()
  const customers = (await customersResp.json()) as Array<{ id: string; name: string }>
  const customer = customers.find((item) => item.name === accountName)
  expect(customer).toBeTruthy()

  const oppsResp = await request.get('http://127.0.0.1:8000/api/guided-quotes/opportunities?search=' + encodeURIComponent(opportunityName), {
    headers: authHeaders,
  })
  expect(oppsResp.ok()).toBeTruthy()
  const opportunities = (await oppsResp.json()) as Array<{ id: string; name: string; customer_id: string }>
  const opportunity = opportunities.find((item) => item.name === opportunityName && item.customer_id === customer!.id)
  expect(opportunity).toBeTruthy()

  const priceBooksResp = await request.get('http://127.0.0.1:8000/api/price-books', { headers: authHeaders })
  expect(priceBooksResp.ok()).toBeTruthy()
  const priceBooks = (await priceBooksResp.json()) as Array<{ id: string; name: string }>
  expect(priceBooks.length).toBeGreaterThan(0)
  const targetPriceBook = priceBooks[0]

  const catalogResp = await request.post('http://127.0.0.1:8000/api/catalog/items', {
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    data: {
      item_code: catalogCode,
      name: catalogName,
      item_type: 'SERVICE',
      versionable: true,
    },
  })
  expect(catalogResp.ok()).toBeTruthy()
  const catalogItem = (await catalogResp.json()) as { id: string }

  const pricingEntryResp = await request.post('http://127.0.0.1:8000/api/price-books/entries', {
    headers: { ...authHeaders, 'Content-Type': 'application/json' },
    data: {
      price_book_id: targetPriceBook.id,
      commercial_item_id: catalogItem.id,
      pricing_model: 'FIXED_PRICE',
      base_price: 1000,
      min_price: 800,
      max_discount_pct: 20,
      currency: 'USD',
      region: 'US',
    },
  })
  expect(pricingEntryResp.ok()).toBeTruthy()

  await page.getByRole('button', { name: 'Sign Out' }).click()
  await page.getByLabel('Work Email').fill('user@spt.com')
  await page.getByLabel('Password').fill('r@ndom11')
  await page.getByLabel('Tenant ID').fill(tenantId)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page.getByRole('heading', { name: 'Normal User Workspace' })).toBeVisible()

  await page.getByRole('button', { name: 'Quote Creation' }).click()
  await page.getByRole('button', { name: new RegExp(accountName) }).first().click()
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByRole('button', { name: new RegExp(opportunityName) }).first().click()
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByRole('button', { name: 'Next' }).click()
  const generalPane = page.locator('.guided-step-pane').filter({ hasText: 'General Questions' })
  await generalPane.locator('select').nth(1).selectOption(targetPriceBook.id)
  await page.getByRole('button', { name: 'Next' }).click()
  const productsPane = page.locator('.guided-step-pane').filter({ hasText: 'Products, Quantities, Discounts' })
  await productsPane.locator('select').first().selectOption(catalogItem.id)
  await page.getByRole('button', { name: 'Next' }).click()
  await page.getByRole('button', { name: 'Generate Quote' }).click()
  await expect(page.getByText('Review and Regenerate')).toBeVisible()
  await expect(page.getByText(/Quote:\s*Q-/)).toBeVisible()

  const quotesResp = await request.get('http://127.0.0.1:8000/api/quotes', { headers: authHeaders })
  expect(quotesResp.ok()).toBeTruthy()
  const quotes = (await quotesResp.json()) as Array<{ customer_external_id: string; opportunity_id: string; price_book_id: string }>
  const linkedQuote = quotes.find(
    (q) => q.customer_external_id === customer!.id && q.opportunity_id === opportunity!.id && q.price_book_id === targetPriceBook.id,
  )
  expect(linkedQuote).toBeTruthy()
})
