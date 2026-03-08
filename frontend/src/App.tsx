import { FormEvent, useEffect, useMemo, useState } from 'react'
import './index.css'

type UserRole = 'ADMIN' | 'SALES' | 'OPERATIONS' | 'FINANCE' | 'DELIVERY' | 'LEADERSHIP'
type AdminModule = 'ORG' | 'USERS' | 'ACCESS' | 'GOVERNANCE'
type FunctionModule =
  | 'DASHBOARD'
  | 'ACCOUNTS'
  | 'CONTACTS'
  | 'OPPORTUNITIES'
  | 'PIPELINE'
  | 'PRICEBOOKS'
  | 'CATALOG'
  | 'RULES'
  | 'RATECARDS'
  | 'APPROVAL_POLICIES'
type AdminSetupView = AdminModule | FunctionModule
type EndUserModule = 'DASHBOARD' | 'QUOTE_CREATE' | 'REVISIONS' | 'APPROVALS' | 'OUTPUT'
type ApprovalAction = 'APPROVE' | 'REJECT' | 'REQUEST_CHANGES'

type CatalogItem = { id: string; item_code: string; name: string; item_type: string; is_active?: boolean }
type PriceBook = { id: string; name: string; currency: string; status: string }
type PriceBookEntry = {
  id: string
  price_book_id: string
  commercial_item_id: string
  pricing_model: string
  base_price?: number
  min_price?: number
  max_discount_pct?: number
  region?: string
  currency?: string
  metadata_json?: Record<string, any>
}
type Quote = {
  id: string
  quote_no: string
  status: string
  grand_total: number
  margin_pct: number
  price_book_id: string
  currency: string
  region?: string
}
type QuoteLine = {
  id: string
  line_no: number
  commercial_item_id: string
  quantity: number
  discount_pct: number
  list_price?: number
  unit_price?: number
  net_price?: number
}
type Metrics = {
  total_quotes: number
  draft_quotes: number
  pending_approvals: number
  finalized_quotes: number
  total_pipeline_value: number
  average_margin_pct: number
}

type LocalUser = {
  id: string
  email: string
  role: UserRole | 'CUSTOM'
  active: boolean
}

type RevisionDiffRow = {
  key: string
  change: 'ADDED' | 'REMOVED' | 'MODIFIED'
  before: string
  after: string
}
type CrmAccount = {
  id: string
  name: string
  external_id: string
  segment: string
  industry?: string
  website?: string
  owner?: string
  active?: boolean
}
type CrmContact = {
  id: string
  customer_id: string
  name: string
  email: string
  phone?: string
  title?: string
  role?: string
  status?: string
  is_primary?: boolean
}
type CrmOpportunity = {
  id: string
  customer_id: string
  record_type: 'LEAD' | 'OPPORTUNITY'
  name: string
  stage: string
  amount: number
  close_date?: string
  probability_pct?: number
  owner?: string
  status?: string
}

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const defaultRoleMatrix: Record<string, Record<string, boolean>> = {
  ADMIN: {
    'admin:manage': true,
    'admin:org:read': true,
    'admin:org:write': true,
    'admin:user:read': true,
    'admin:user:write': true,
    'admin:rbac:read': true,
    'admin:rbac:write': true,
    'admin:governance:read': true,
    'admin:governance:write': true,
    'catalog:read': true,
    'catalog:write': true,
    'pricebook:read': true,
    'pricebook:write': true,
    'quote:read': true,
    'quote:write': true,
    'approval:act': true,
    'dashboard:read': true,
    'async:run': true,
  },
  SALES: {
    'catalog:read': true,
    'pricebook:read': true,
    'quote:read': true,
    'quote:write': true,
    'approval:act': true,
    'dashboard:read': true,
  },
  OPERATIONS: {
    'catalog:read': true,
    'pricebook:read': true,
    'pricebook:write': true,
    'quote:read': true,
    'quote:write': true,
    'dashboard:read': true,
  },
  FINANCE: {
    'catalog:read': true,
    'pricebook:read': true,
    'quote:read': true,
    'approval:act': true,
    'dashboard:read': true,
  },
  DELIVERY: {
    'catalog:read': true,
    'pricebook:read': true,
    'quote:read': true,
    'quote:write': true,
    'dashboard:read': true,
  },
  LEADERSHIP: {
    'catalog:read': true,
    'pricebook:read': true,
    'quote:read': true,
    'approval:act': true,
    'dashboard:read': true,
  },
}

function App() {
  const [tenantId, setTenantId] = useState(localStorage.getItem('tenantId') || crypto.randomUUID())
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [refreshingCore, setRefreshingCore] = useState(false)
  const [token, setToken] = useState(localStorage.getItem('token') || '')
  const [authProfile, setAuthProfile] = useState<{ roles: string[]; permissions: string[] } | null>(null)

  const [adminModule, setAdminModule] = useState<AdminModule>('ORG')
  const [functionModule, setFunctionModule] = useState<FunctionModule>('DASHBOARD')
  const [adminSetupView, setAdminSetupView] = useState<AdminSetupView>('ORG')
  const [endUserModule, setEndUserModule] = useState<EndUserModule>('DASHBOARD')

  const [catalogItems, setCatalogItems] = useState<CatalogItem[]>([])
  const [priceBooks, setPriceBooks] = useState<PriceBook[]>([])
  const [entries, setEntries] = useState<PriceBookEntry[]>([])
  const [quotes, setQuotes] = useState<Quote[]>([])
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [auditEvents, setAuditEvents] = useState<any[]>([])
  const [obsMetrics, setObsMetrics] = useState<any | null>(null)

  const [quoteDraft, setQuoteDraft] = useState({
    customer_external_id: '',
    customer_account_id: '',
    opportunity_id: '',
    currency: 'USD',
    region: 'US',
    price_book_id: '',
  })
  const [lineDraft, setLineDraft] = useState({ commercial_item_id: '', quantity: 1, discount_pct: 0 })
  const [guidedStep, setGuidedStep] = useState(1)
  const [guidedCustomerSearch, setGuidedCustomerSearch] = useState('')
  const [guidedCustomers, setGuidedCustomers] = useState<any[]>([])
  const [guidedCustomersLoading, setGuidedCustomersLoading] = useState(false)
  const [guidedCustomerName, setGuidedCustomerName] = useState('')
  const [guidedSelectedCustomerId, setGuidedSelectedCustomerId] = useState('')
  const [guidedOpportunitySearch, setGuidedOpportunitySearch] = useState('')
  const [guidedOpportunities, setGuidedOpportunities] = useState<any[]>([])
  const [guidedOpportunitiesLoading, setGuidedOpportunitiesLoading] = useState(false)
  const [guidedOpportunityName, setGuidedOpportunityName] = useState('')
  const [guidedSelectedOpportunityId, setGuidedSelectedOpportunityId] = useState('')
  const [guidedCustomerQuotes, setGuidedCustomerQuotes] = useState<Quote[]>([])
  const [guidedQuotesLoading, setGuidedQuotesLoading] = useState(false)
  const [guidedCloneQuoteId, setGuidedCloneQuoteId] = useState('')
  const [guidedGeneral, setGuidedGeneral] = useState({
    duration_type: 'ONETIME',
    duration_value: 1,
    valid_until: '',
    price_book_id: '',
    currency: 'USD',
    region: 'US',
    overall_discount_pct: 0,
  })
  const [guidedLines, setGuidedLines] = useState<Array<{ commercial_item_id: string; quantity_per_period: number; line_discount_pct: number }>>([
    { commercial_item_id: '', quantity_per_period: 1, line_discount_pct: 0 },
  ])
  const [guidedResult, setGuidedResult] = useState<any | null>(null)
  const [guidedGenerating, setGuidedGenerating] = useState(false)
  const [currentQuoteId, setCurrentQuoteId] = useState('')
  const [quoteLines, setQuoteLines] = useState<QuoteLine[]>([])
  const [preview, setPreview] = useState<any>(null)
  const [revisions, setRevisions] = useState<any[]>([])
  const [approvalState, setApprovalState] = useState<any | null>(null)
  const [approvalTimeline, setApprovalTimeline] = useState<any[]>([])
  const [approvalComments, setApprovalComments] = useState('')
  const [aiRisk, setAiRisk] = useState<any | null>(null)
  const [aiSuggestions, setAiSuggestions] = useState<any | null>(null)
  const [lastPdfJob, setLastPdfJob] = useState<any | null>(null)

  const [orgSettings, setOrgSettings] = useState({
    name: 'SANCNIDA Corp',
    region: 'US',
    timezone: 'America/New_York',
    default_currency: 'USD',
    fiscal_year_start: '2026-01-01',
    tax_behavior: 'CALCULATED',
    primary_color: '#0f8f7a',
    logo_url: '',
  })
  const [featureFlags, setFeatureFlags] = useState({
    pricing_simulator_v2: true,
    approval_risk_panel: true,
    advanced_anomalies: true,
  })
  const [users, setUsers] = useState<LocalUser[]>([
    { id: crypto.randomUUID(), email: 'admin@tenant.com', role: 'ADMIN', active: true },
    { id: crypto.randomUUID(), email: 'sales@tenant.com', role: 'SALES', active: true },
    { id: crypto.randomUUID(), email: 'ops@tenant.com', role: 'OPERATIONS', active: true },
  ])
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<LocalUser['role']>('SALES')
  const [roleMatrix, setRoleMatrix] = useState(defaultRoleMatrix)

  const [newPriceBook, setNewPriceBook] = useState({ name: 'Regional Strategy', currency: 'USD' })
  const [priceBookEditDraft, setPriceBookEditDraft] = useState<{ id: string; name: string; currency: string } | null>(null)
  const [pricingConfig, setPricingConfig] = useState({
    price_book_id: '',
    commercial_item_id: '',
    pricing_model: 'FIXED_PRICE',
    base_price: 100,
    min_price: 70,
    max_discount_pct: 20,
    currency: 'USD',
    region: 'US',
    tiers_json: '[{"min":1,"max":10,"price":100},{"min":11,"max":50,"price":90}]',
  })
  const [simInput, setSimInput] = useState({ quantity: 5, discount_pct: 10 })
  const [simResult, setSimResult] = useState<any>(null)

  const [catalogDraft, setCatalogDraft] = useState({ item_code: '', name: '', item_type: 'SERVICE' })
  const [ruleDraft, setRuleDraft] = useState({
    name: 'High Discount Guardrail',
    rule_type: 'VALIDATION',
    priority: 100,
    when_key: 'region',
    when_value: 'US',
    then_key: 'warning',
    then_value: 'Check margin impact',
  })
  const [rules, setRules] = useState<any[]>([])

  const [rateCardRows, setRateCardRows] = useState([
    { role: 'Architect', delivery: 'ONSITE', rate: 250, region: 'US', effective: '2026-01-01' },
    { role: 'Analyst', delivery: 'OFFSHORE', rate: 90, region: 'IN', effective: '2026-01-01' },
  ])
  const [rateCardDraft, setRateCardDraft] = useState({ role: '', delivery: 'REMOTE', rate: 100, region: 'US', effective: '2026-01-01' })
  const [rateBulkPct, setRateBulkPct] = useState(5)

  const [approvalPolicyDraft, setApprovalPolicyDraft] = useState({
    name: 'Margin Threshold Policy',
    min_grand_total: 50000,
    max_margin_pct: 18,
    levels: 2,
  })
  const [approvalPolicies, setApprovalPolicies] = useState<any[]>([])

  const [quoteSearch, setQuoteSearch] = useState('')
  const [quoteStatusFilter, setQuoteStatusFilter] = useState('ALL')
  const [crmAccounts, setCrmAccounts] = useState<CrmAccount[]>([])
  const [crmContacts, setCrmContacts] = useState<CrmContact[]>([])
  const [crmOpportunities, setCrmOpportunities] = useState<CrmOpportunity[]>([])
  const [crmLifecycle, setCrmLifecycle] = useState<{ lead: string[]; opportunity: string[] }>({ lead: [], opportunity: [] })
  const [crmPipeline, setCrmPipeline] = useState<any | null>(null)
  const [accountSearch, setAccountSearch] = useState('')
  const [contactSearch, setContactSearch] = useState('')
  const [dealSearch, setDealSearch] = useState('')
  const [dealTypeFilter, setDealTypeFilter] = useState<'ALL' | 'LEAD' | 'OPPORTUNITY'>('ALL')
  const [accountDraft, setAccountDraft] = useState({ name: '', external_id: '', segment: 'SMB', industry: '', website: '', owner: '' })
  const [contactDraft, setContactDraft] = useState({ customer_id: '', name: '', email: '', phone: '', title: '', role: 'STAKEHOLDER' })
  const [dealDraft, setDealDraft] = useState({
    customer_id: '',
    record_type: 'LEAD',
    name: '',
    stage: 'NEW',
    amount: 0,
    close_date: '',
    probability_pct: 20,
    owner: '',
    source: 'MANUAL',
  })
  const [catalogSearch, setCatalogSearch] = useState('')
  const [catalogFilter, setCatalogFilter] = useState('ALL')
  const [favoriteItemIds, setFavoriteItemIds] = useState<string[]>([])
  const [recentItemIds, setRecentItemIds] = useState<string[]>([])
  const [selectedCatalogItemId, setSelectedCatalogItemId] = useState('')
  const [expandedLineIds, setExpandedLineIds] = useState<string[]>([])
  const [lineEdits, setLineEdits] = useState<Record<string, { quantity: number; discount_pct: number }>>({})
  const [saveState, setSaveState] = useState<'SAVED' | 'DIRTY' | 'SAVING'>('SAVED')
  const [lastSavedAt, setLastSavedAt] = useState('')
  const [pricingDrawerOpen, setPricingDrawerOpen] = useState(false)
  const [selectedExplainLineId, setSelectedExplainLineId] = useState('')
  const [simQuantity, setSimQuantity] = useState(1)
  const [simDiscount, setSimDiscount] = useState(0)
  const [decisionCompactMode, setDecisionCompactMode] = useState(false)
  const [decisionAdjustDiscount, setDecisionAdjustDiscount] = useState(0)
  const [decisionComment, setDecisionComment] = useState('')

  const activeRole = useMemo(() => authProfile?.roles?.[0] || 'UNKNOWN', [authProfile])
  const permissionSet = useMemo(() => new Set(authProfile?.permissions || []), [authProfile?.permissions])
  const isAdmin = permissionSet.has('admin:manage')
  const canUseFunctionalSetup = isAdmin && (permissionSet.has('pricebook:write') || permissionSet.has('catalog:write'))
  const canUseMiniCrm = permissionSet.has('quote:read') || permissionSet.has('quote:write') || permissionSet.has('dashboard:read')
  const workspaceTitle = isAdmin ? 'Admin Workspace' : 'Normal User Workspace'
  const workspaceSubtitle = isAdmin
    ? 'System setup and functional setup controls'
    : `Role: ${activeRole} | Sales, Operations, Finance, Delivery, Leadership`

  const headers = useMemo(
    () => ({
      'Content-Type': 'application/json',
      'X-Tenant-Id': tenantId,
      Authorization: `Bearer ${token}`,
      'X-User-Sub': email || 'ui-user',
    }),
    [tenantId, token, email],
  )

  const filteredQuotes = useMemo(() => {
    const q = quoteSearch.trim().toLowerCase()
    return quotes.filter((quote) => {
      const statusOk = quoteStatusFilter === 'ALL' || quote.status === quoteStatusFilter
      const searchOk = q.length === 0 || quote.quote_no.toLowerCase().includes(q)
      return statusOk && searchOk
    })
  }, [quotes, quoteSearch, quoteStatusFilter])

  const filteredAccounts = useMemo(() => {
    const q = accountSearch.trim().toLowerCase()
    if (!q) return crmAccounts
    return crmAccounts.filter((account) => {
      const hay = `${account.name} ${account.external_id} ${account.segment} ${account.industry || ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [crmAccounts, accountSearch])

  const filteredContacts = useMemo(() => {
    const q = contactSearch.trim().toLowerCase()
    if (!q) return crmContacts
    return crmContacts.filter((contact) => {
      const hay = `${contact.name} ${contact.email} ${contact.title || ''}`.toLowerCase()
      return hay.includes(q)
    })
  }, [crmContacts, contactSearch])

  const filteredDeals = useMemo(() => {
    const q = dealSearch.trim().toLowerCase()
    return crmOpportunities.filter((deal) => {
      const typeOk = dealTypeFilter === 'ALL' || deal.record_type === dealTypeFilter
      const searchOk = q.length === 0 || `${deal.name} ${deal.stage}`.toLowerCase().includes(q)
      return typeOk && searchOk
    })
  }, [crmOpportunities, dealSearch, dealTypeFilter])

  const currentQuote = useMemo(() => quotes.find((q) => q.id === currentQuoteId) || null, [quotes, currentQuoteId])

  const catalogTypes = useMemo(
    () => ['ALL', ...Array.from(new Set(catalogItems.map((item) => item.item_type)))],
    [catalogItems],
  )

  const filteredCatalogItems = useMemo(() => {
    const q = catalogSearch.trim().toLowerCase()
    return catalogItems.filter((item) => {
      const text = `${item.item_code} ${item.name}`.toLowerCase()
      const searchOk = q.length === 0 || text.includes(q)
      const typeOk = catalogFilter === 'ALL' || item.item_type === catalogFilter
      return searchOk && typeOk
    })
  }, [catalogItems, catalogFilter, catalogSearch])

  const selectedCatalogItem = useMemo(
    () => catalogItems.find((item) => item.id === selectedCatalogItemId) || null,
    [catalogItems, selectedCatalogItemId],
  )
  const selectedGuidedCustomer = useMemo(
    () => guidedCustomers.find((customer) => customer.id === guidedSelectedCustomerId) || null,
    [guidedCustomers, guidedSelectedCustomerId],
  )
  const selectedGuidedOpportunity = useMemo(
    () => guidedOpportunities.find((opportunity) => opportunity.id === guidedSelectedOpportunityId) || null,
    [guidedOpportunities, guidedSelectedOpportunityId],
  )
  const selectedGuidedPriceBook = useMemo(
    () => priceBooks.find((book) => book.id === guidedGeneral.price_book_id) || null,
    [priceBooks, guidedGeneral.price_book_id],
  )
  const guidedQuoteTerm = useMemo(() => {
    if (guidedGeneral.duration_type === 'ONETIME') return 'Onetime'
    const unit = guidedGeneral.duration_type === 'YEARS' ? 'Year(s)' : 'Month(s)'
    return `${guidedGeneral.duration_value} ${unit}`
  }, [guidedGeneral.duration_type, guidedGeneral.duration_value])
  const guidedQuoteCurrency = guidedResult?.quote?.currency || guidedGeneral.currency || quoteDraft.currency || 'USD'
  const guidedQuoteTotal = Number(guidedResult?.preview?.grand_total ?? preview?.grand_total ?? 0)
  const guidedSummaryProgress = useMemo(() => {
    let completed = 0
    if (selectedGuidedCustomer?.name) completed += 1
    if (selectedGuidedOpportunity?.name) completed += 1
    if (selectedGuidedPriceBook?.name) completed += 1
    if (guidedQuoteTotal > 0) completed += 1
    return Math.round((completed / 4) * 100)
  }, [selectedGuidedCustomer?.name, selectedGuidedOpportunity?.name, selectedGuidedPriceBook?.name, guidedQuoteTotal])

  const approvalImpact = useMemo(() => {
    const total = preview?.grand_total ?? 0
    const margin = preview?.margin_pct ?? 100
    if (total >= 100000 || margin < 15) return 'Finance and executive approval likely required.'
    if (total >= 25000 || margin < 22) return 'Manager approval likely required.'
    return 'No additional approval predicted from current thresholds.'
  }, [preview?.grand_total, preview?.margin_pct])

  const selectedExplanation = useMemo(() => {
    const list = preview?.pricing_explanations || []
    return list.find((item: any) => item.line_id === selectedExplainLineId) || null
  }, [preview?.pricing_explanations, selectedExplainLineId])

  const currentApprovalStep = useMemo(() => {
    if (!approvalState?.steps) return null
    return approvalState.steps.find((step: any) => step.status === 'PENDING') || approvalState.steps[approvalState.steps.length - 1] || null
  }, [approvalState?.steps])

  const approvalAgeHours = useMemo(() => {
    if (!approvalState?.started_at) return 0
    const started = new Date(approvalState.started_at).getTime()
    const now = Date.now()
    return Math.max(0, Math.round((now - started) / (1000 * 60 * 60)))
  }, [approvalState?.started_at])

  const approvalDelta = useMemo(() => {
    if (revisions.length < 2) return null
    const latest = revisions[revisions.length - 1]?.snapshot_json?.quote
    const prev = revisions[revisions.length - 2]?.snapshot_json?.quote
    if (!latest || !prev) return null
    return {
      grandTotalFrom: Number(prev.grand_total || 0),
      grandTotalTo: Number(latest.grand_total || 0),
      marginFrom: Number(prev.margin_pct || 0),
      marginTo: Number(latest.margin_pct || 0),
    }
  }, [revisions])

  const decisionRisks = useMemo(() => {
    const risks: string[] = []
    for (const sig of preview?.approval_signals || []) risks.push(sig.message)
    if ((preview?.margin_pct ?? 100) < 35) risks.push(`Margin below target: ${(preview?.margin_pct ?? 0).toFixed(2)}%`)
    if ((preview?.discount_total ?? 0) > 0) risks.push(`Discount present: $${(preview?.discount_total ?? 0).toFixed(2)}`)
    if (approvalTimeline.some((step) => step.status === 'PENDING' && step.sla_due_at && new Date(step.sla_due_at) < new Date())) {
      risks.push('SLA breached on pending approval step')
    }
    return Array.from(new Set(risks))
  }, [preview?.approval_signals, preview?.margin_pct, preview?.discount_total, approvalTimeline])

  const blockingErrors = useMemo(() => {
    const errors: string[] = []
    if (lineDraft.quantity <= 0) errors.push('Quantity must be greater than 0')
    if (lineDraft.discount_pct > 100) errors.push('Discount cannot exceed 100%')
    if (!quoteDraft.price_book_id && !isAdmin) errors.push('Price book is required before quote creation')
    return errors
  }, [lineDraft, quoteDraft.price_book_id, isAdmin])

  const warnings = useMemo(() => {
    const notes: string[] = []
    if (lineDraft.discount_pct > 25) notes.push('High discount: review approval thresholds')
    if ((preview?.margin_pct ?? 100) < 15) notes.push('Low margin detected: may trigger approvals')
    return notes
  }, [lineDraft.discount_pct, preview?.margin_pct])

  async function request(path: string, options: RequestInit = {}) {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...headers, ...(options.headers || {}) },
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(data.detail || 'Request failed')
    }

    if (response.status === 204) return null
    return response.json()
  }

  async function getDevToken(userEmail: string, userPassword: string) {
    const response = await fetch(`${API_BASE}/api/auth/dev-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tenant_id: tenantId, email: userEmail, password: userPassword }),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({ detail: 'Authentication failed' }))
      throw new Error(data.detail || 'Authentication failed')
    }
    const data = await response.json()
    const accessToken = data.access_token as string
    setToken(accessToken)
    localStorage.setItem('token', accessToken)
    localStorage.setItem('tenantId', tenantId)
    return accessToken
  }

  async function hydrateAuthContext(accessToken: string) {
    const response = await fetch(`${API_BASE}/api/auth/me`, {
      headers: {
        'Content-Type': 'application/json',
        'X-Tenant-Id': tenantId,
        Authorization: `Bearer ${accessToken}`,
        'X-User-Sub': email || 'ui-user',
      },
    })
    if (!response.ok) throw new Error('Failed to load user permissions')
    const data = await response.json()
    setAuthProfile({
      roles: data.roles || [],
      permissions: data.permissions || [],
    })
  }

  async function signIn(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    setStatus('Signing in...')
    try {
      const accessToken = await getDevToken(email, password)
      await hydrateAuthContext(accessToken)
      setStatus('Signed in')
    } catch (error: any) {
      setStatus(error.message || 'Sign in failed')
    } finally {
      setLoading(false)
    }
  }

  async function ssoSignIn() {
    setLoading(true)
    setStatus('Redirecting to SSO...')
    try {
      const accessToken = await getDevToken(email, password)
      await hydrateAuthContext(accessToken)
      setStatus('SSO handshake simulated')
    } catch (error: any) {
      setStatus(error.message || 'SSO failed')
    } finally {
      setLoading(false)
    }
  }

  function signOut() {
    setToken('')
    setAuthProfile(null)
    localStorage.removeItem('token')
    setStatus('Signed out')
  }

  async function refreshCore() {
    if (!token) return
    setRefreshingCore(true)
    try {
      const [items, books, quoteList, dash, audits, obs] = await Promise.all([
        request('/api/catalog/items'),
        request('/api/price-books'),
        request('/api/quotes'),
        request('/api/analytics/dashboard'),
        request('/api/audit/events').catch(() => []),
        request('/api/observability/metrics').catch(() => null),
      ])
      setCatalogItems(items)
      setPriceBooks(books)
      setQuotes(quoteList)
      setMetrics(dash)
      setAuditEvents(audits)
      setObsMetrics(obs)

      if (!quoteDraft.price_book_id && books.length > 0) {
        setQuoteDraft((prev) => ({ ...prev, price_book_id: books[0].id, currency: books[0].currency }))
      }
      if (!pricingConfig.price_book_id && books.length > 0) {
        setPricingConfig((prev) => ({ ...prev, price_book_id: books[0].id, currency: books[0].currency }))
      }
      if (!guidedGeneral.price_book_id && books.length > 0) {
        setGuidedGeneral((prev) => ({ ...prev, price_book_id: books[0].id, currency: books[0].currency }))
      }
      if (!lineDraft.commercial_item_id && items.length > 0) {
        setLineDraft((prev) => ({ ...prev, commercial_item_id: items[0].id }))
      }
      if (!pricingConfig.commercial_item_id && items.length > 0) {
        setPricingConfig((prev) => ({ ...prev, commercial_item_id: items[0].id }))
      }
    } catch (error: any) {
      setStatus(error.message)
    } finally {
      setRefreshingCore(false)
    }
  }

  async function loadAdminData() {
    if (!token || !isAdmin) return
    try {
      const [org, usr, matrix, flags, rates] = await Promise.all([
        request('/api/admin/org-settings'),
        request('/api/admin/users'),
        request('/api/admin/role-matrix'),
        request('/api/admin/feature-flags'),
        request('/api/admin/rate-cards').catch(() => []),
      ])
      setOrgSettings(org)
      setUsers(usr)
      setRoleMatrix(matrix)
      setFeatureFlags(flags)
      setRateCardRows(rates)
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function loadFunctionData() {
    if (!token || !canUseFunctionalSetup) return
    try {
      const [entryList, ruleList, policyList] = await Promise.all([
        pricingConfig.price_book_id ? request(`/api/price-books/${pricingConfig.price_book_id}/entries`).catch(() => []) : Promise.resolve([]),
        request('/api/rules').catch(() => []),
        request('/api/approval-policies').catch(() => []),
      ])
      setEntries(entryList)
      setRules(ruleList)
      setApprovalPolicies(policyList)
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function loadMiniCrmData() {
    if (!token || !canUseMiniCrm) return
    try {
      const [accounts, contacts, opportunities, lifecycle, pipeline] = await Promise.all([
        request(`/api/guided-quotes/customers?search=${encodeURIComponent(accountSearch)}`),
        request(`/api/guided-quotes/contacts?search=${encodeURIComponent(contactSearch)}`).catch(() => []),
        request(`/api/guided-quotes/opportunities?search=${encodeURIComponent(dealSearch)}${dealTypeFilter === 'ALL' ? '' : `&record_type=${dealTypeFilter}`}`).catch(() => []),
        request('/api/guided-quotes/lifecycle').catch(() => ({ lead: [], opportunity: [] })),
        request('/api/guided-quotes/pipeline/summary').catch(() => null),
      ])
      setCrmAccounts(accounts)
      setCrmContacts(contacts)
      setCrmOpportunities(opportunities)
      setCrmLifecycle(lifecycle)
      setCrmPipeline(pipeline)
      if (!contactDraft.customer_id && accounts.length > 0) {
        setContactDraft((prev) => ({ ...prev, customer_id: accounts[0].id }))
      }
      if (!dealDraft.customer_id && accounts.length > 0) {
        setDealDraft((prev) => ({ ...prev, customer_id: accounts[0].id }))
      }
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createAccount(e: FormEvent) {
    e.preventDefault()
    if (!accountDraft.name.trim()) return
    try {
      await request('/api/guided-quotes/customers', {
        method: 'POST',
        body: JSON.stringify(accountDraft),
      })
      setAccountDraft({ name: '', external_id: '', segment: 'SMB', industry: '', website: '', owner: '' })
      setStatus('Account created')
      await loadMiniCrmData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function deleteAccount(accountId: string) {
    const ok = window.confirm('Delete this account and all linked contacts/deals?')
    if (!ok) return
    try {
      await request(`/api/guided-quotes/customers/${accountId}`, { method: 'DELETE' })
      setStatus('Account deleted')
      await loadMiniCrmData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createContactRecord(e: FormEvent) {
    e.preventDefault()
    if (!contactDraft.customer_id || !contactDraft.email.trim()) return
    try {
      await request('/api/guided-quotes/contacts', {
        method: 'POST',
        body: JSON.stringify(contactDraft),
      })
      setContactDraft((prev) => ({ ...prev, name: '', email: '', phone: '', title: '' }))
      setStatus('Contact saved')
      await loadMiniCrmData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function deleteContactRecord(contactId: string) {
    try {
      await request(`/api/guided-quotes/contacts/${contactId}`, { method: 'DELETE' })
      setStatus('Contact deleted')
      await loadMiniCrmData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createDeal(e: FormEvent) {
    e.preventDefault()
    if (!dealDraft.customer_id || !dealDraft.name.trim()) return
    try {
      await request('/api/guided-quotes/opportunities', {
        method: 'POST',
        body: JSON.stringify({
          ...dealDraft,
          amount: Number(dealDraft.amount || 0),
          probability_pct: Number(dealDraft.probability_pct || 0),
          close_date: dealDraft.close_date || null,
        }),
      })
      setDealDraft((prev) => ({ ...prev, name: '', amount: 0, probability_pct: 20, close_date: '' }))
      setStatus('Lead/Opportunity created')
      await loadMiniCrmData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function moveDealStage(opportunityId: string, stage: string) {
    try {
      await request(`/api/guided-quotes/opportunities/${opportunityId}`, {
        method: 'PATCH',
        body: JSON.stringify({ stage }),
      })
      setStatus(`Deal moved to ${stage}`)
      await loadMiniCrmData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function deleteDeal(opportunityId: string) {
    try {
      await request(`/api/guided-quotes/opportunities/${opportunityId}`, { method: 'DELETE' })
      setStatus('Deal deleted')
      await loadMiniCrmData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function loadGuidedCustomers(search = '') {
    if (!token) return
    setGuidedCustomersLoading(true)
    try {
      const data = await request(`/api/guided-quotes/customers?search=${encodeURIComponent(search)}`)
      setGuidedCustomers(data)
    } catch (error: any) {
      setStatus(error.message)
    } finally {
      setGuidedCustomersLoading(false)
    }
  }

  async function loadGuidedOpportunities(customerId: string, search = '') {
    if (!token || !customerId) return
    setGuidedOpportunitiesLoading(true)
    try {
      const data = await request(`/api/guided-quotes/opportunities?customer_id=${encodeURIComponent(customerId)}&search=${encodeURIComponent(search)}`)
      setGuidedOpportunities(data)
    } catch (error: any) {
      setStatus(error.message)
    } finally {
      setGuidedOpportunitiesLoading(false)
    }
  }

  async function loadCustomerQuoteHistory(customerId: string) {
    if (!token || !customerId) return
    setGuidedQuotesLoading(true)
    try {
      const data = await request(`/api/guided-quotes/customers/${customerId}/quotes`)
      setGuidedCustomerQuotes(data)
    } catch (error: any) {
      setStatus(error.message)
    } finally {
      setGuidedQuotesLoading(false)
    }
  }

  async function createGuidedCustomer() {
    if (!guidedCustomerName.trim()) return
    try {
      const customer = await request('/api/guided-quotes/customers', {
        method: 'POST',
        body: JSON.stringify({ name: guidedCustomerName.trim() }),
      })
      setGuidedCustomerName('')
      setGuidedSelectedCustomerId(customer.id)
      await loadGuidedCustomers(guidedCustomerSearch)
      await loadGuidedOpportunities(customer.id)
      setStatus(`Customer created: ${customer.name}`)
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createGuidedOpportunity() {
    if (!guidedSelectedCustomerId || !guidedOpportunityName.trim()) return
    try {
      const opp = await request('/api/guided-quotes/opportunities', {
        method: 'POST',
        body: JSON.stringify({
          customer_id: guidedSelectedCustomerId,
          name: guidedOpportunityName.trim(),
          stage: 'QUALIFICATION',
          amount: 0,
        }),
      })
      setGuidedOpportunityName('')
      setGuidedSelectedOpportunityId(opp.id)
      await loadGuidedOpportunities(guidedSelectedCustomerId, guidedOpportunitySearch)
      setStatus(`Opportunity created: ${opp.name}`)
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  function updateGuidedLine(index: number, patch: Partial<{ commercial_item_id: string; quantity_per_period: number; line_discount_pct: number }>) {
    setGuidedLines((prev) => prev.map((line, idx) => (idx === index ? { ...line, ...patch } : line)))
  }

  function addGuidedLine() {
    setGuidedLines((prev) => [...prev, { commercial_item_id: '', quantity_per_period: 1, line_discount_pct: 0 }])
  }

  function removeGuidedLine(index: number) {
    setGuidedLines((prev) => prev.filter((_, idx) => idx !== index))
  }

  function buildGuidedSchedule(quantityPerPeriod: number) {
    const periods = guidedGeneral.duration_type === 'ONETIME' ? 1 : Math.max(1, Number(guidedGeneral.duration_value || 1))
    const schedule: Record<number, number> = {}
    for (let idx = 1; idx <= periods; idx += 1) schedule[idx] = Number(quantityPerPeriod || 0)
    return schedule
  }

  async function generateGuidedQuote() {
    if (!guidedSelectedCustomerId) {
      setStatus('Select a customer first')
      return
    }
    if (!guidedGeneral.price_book_id) {
      setStatus('Select a price book in general questions')
      return
    }

    const lineItems = guidedLines
      .filter((line) => line.commercial_item_id)
      .map((line) => ({
        commercial_item_id: line.commercial_item_id,
        line_discount_pct: Number(line.line_discount_pct || 0),
        quantity_schedule: buildGuidedSchedule(Number(line.quantity_per_period || 0)),
      }))

    if (lineItems.length === 0 && !guidedCloneQuoteId) {
      setStatus('Add at least one product line or choose quote clone')
      return
    }

    setGuidedGenerating(true)
    try {
      const generated = await request('/api/guided-quotes/generate', {
        method: 'POST',
        body: JSON.stringify({
          customer_id: guidedSelectedCustomerId,
          opportunity_id: guidedSelectedOpportunityId || null,
          clone_quote_id: guidedCloneQuoteId || null,
          general: {
            duration_type: guidedGeneral.duration_type,
            duration_value: Number(guidedGeneral.duration_value || 1),
            valid_until: guidedGeneral.valid_until || null,
            price_book_id: guidedGeneral.price_book_id,
            currency: guidedGeneral.currency,
            region: guidedGeneral.region,
            overall_discount_pct: Number(guidedGeneral.overall_discount_pct || 0),
          },
          line_items: lineItems,
        }),
      })

      const quote = generated.quote
      setGuidedResult(generated)
      setCurrentQuoteId(quote.id)
      setQuoteDraft((prev) => ({
        ...prev,
        customer_external_id: quote.customer_external_id || guidedSelectedCustomerId,
        customer_account_id: quote.customer_account_id || guidedSelectedCustomerId,
        opportunity_id: quote.opportunity_id || guidedSelectedOpportunityId,
        price_book_id: quote.price_book_id,
        currency: quote.currency,
        region: quote.region || prev.region,
      }))
      await refreshQuoteDetails(quote.id)
      await refreshCore()
      setGuidedStep(7)
      setStatus(`Guided quote generated: ${quote.quote_no}`)
    } catch (error: any) {
      setStatus(error.message)
    } finally {
      setGuidedGenerating(false)
    }
  }

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'light')
    localStorage.setItem('theme', 'light')
  }, [])

  useEffect(() => {
    if (token) void refreshCore()
  }, [token])

  useEffect(() => {
    if (token && !authProfile) void hydrateAuthContext(token)
  }, [token, authProfile, tenantId, email])

  useEffect(() => {
    if (token && isAdmin) void loadAdminData()
  }, [token, isAdmin])

  useEffect(() => {
    if (token && canUseFunctionalSetup) void loadFunctionData()
  }, [token, canUseFunctionalSetup, pricingConfig.price_book_id])

  useEffect(() => {
    if (token && canUseMiniCrm) void loadMiniCrmData()
  }, [token, canUseMiniCrm, accountSearch, contactSearch, dealSearch, dealTypeFilter])

  useEffect(() => {
    if (!token || isAdmin || endUserModule !== 'QUOTE_CREATE') return
    void loadGuidedCustomers(guidedCustomerSearch)
  }, [token, isAdmin, endUserModule, guidedCustomerSearch])

  useEffect(() => {
    if (!token || !guidedSelectedCustomerId || isAdmin || endUserModule !== 'QUOTE_CREATE') return
    void loadGuidedOpportunities(guidedSelectedCustomerId, guidedOpportunitySearch)
    if (guidedStep >= 3) void loadCustomerQuoteHistory(guidedSelectedCustomerId)
  }, [token, isAdmin, endUserModule, guidedSelectedCustomerId, guidedOpportunitySearch, guidedStep])

  const approvalPendingQuotes = useMemo(
    () => quotes.filter((q) => q.status === 'APPROVAL_PENDING'),
    [quotes],
  )

  async function refreshQuoteDetails(quoteId: string) {
    if (!quoteId) return
    try {
      const [lines, previewResult, revisionList] = await Promise.all([
        request(`/api/quotes/${quoteId}/line-items`),
        request(`/api/quotes/${quoteId}/price-preview`, { method: 'POST' }),
        request(`/api/quotes/${quoteId}/revisions`).catch(() => []),
      ])
      setQuoteLines(lines)
      setLineEdits(
        Object.fromEntries(
          lines.map((line: QuoteLine) => [line.id, { quantity: Number(line.quantity), discount_pct: Number(line.discount_pct) }]),
        ),
      )
      if (lines.length > 0) setDecisionAdjustDiscount(Number(lines[0].discount_pct || 0))
      setPreview(previewResult)
      setRevisions(revisionList)

      const approval = await request(`/api/quotes/${quoteId}/approval`).catch(() => null)
      setApprovalState(approval)
      if (approval?.id) {
        const timeline = await request(`/api/approvals/${approval.id}/timeline`).catch(() => null)
        setApprovalTimeline(timeline?.timeline || [])
      } else {
        setApprovalTimeline([])
      }

      const [risk, suggestion] = await Promise.all([
        request(`/api/ai/quote-risk/${quoteId}`, { method: 'POST' }).catch(() => null),
        request(`/api/ai/pricing-suggestions/${quoteId}`, { method: 'POST' }).catch(() => null),
      ])
      setAiRisk(risk)
      setAiSuggestions(suggestion)
      setSaveState('SAVED')
      setLastSavedAt(new Date().toLocaleTimeString())
      await refreshCore()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function saveDraftQuote() {
    if (blockingErrors.length > 0) {
      setStatus(blockingErrors[0])
      return
    }
    try {
      setSaveState('SAVING')
      const quote = await request('/api/quotes', { method: 'POST', body: JSON.stringify(quoteDraft) })
      setCurrentQuoteId(quote.id)
      setQuoteLines([])
      setPreview(null)
      setStatus(`Draft ${quote.quote_no} created`)
      setSaveState('SAVED')
      setLastSavedAt(new Date().toLocaleTimeString())
      await refreshCore()
    } catch (error: any) {
      setSaveState('DIRTY')
      setStatus(error.message)
    }
  }

  async function createDraftQuote(e: FormEvent) {
    e.preventDefault()
    await saveDraftQuote()
  }

  async function addLineByPayload(payload: { commercial_item_id: string; quantity: number; discount_pct: number }) {
    if (blockingErrors.length > 0) {
      setStatus(blockingErrors[0])
      return
    }
    if (!currentQuoteId) {
      setStatus('Create or select a quote first.')
      return
    }
    try {
      setSaveState('SAVING')
      await request(`/api/quotes/${currentQuoteId}/line-items`, { method: 'POST', body: JSON.stringify(payload) })
      setStatus('Line item added and quote recalculated')
      setRecentItemIds((prev) => [payload.commercial_item_id, ...prev.filter((id) => id !== payload.commercial_item_id)].slice(0, 8))
      setSaveState('SAVED')
      setLastSavedAt(new Date().toLocaleTimeString())
      await refreshQuoteDetails(currentQuoteId)
    } catch (error: any) {
      setSaveState('DIRTY')
      setStatus(error.message)
    }
  }

  async function addLine(e: FormEvent) {
    e.preventDefault()
    await addLineByPayload({
      commercial_item_id: lineDraft.commercial_item_id,
      quantity: Number(lineDraft.quantity),
      discount_pct: Number(lineDraft.discount_pct),
    })
  }

  async function updateLineItem(lineId: string, patch: { quantity?: number; discount_pct?: number }) {
    if (!currentQuoteId) return
    try {
      setSaveState('SAVING')
      await request(`/api/quotes/${currentQuoteId}/line-items/${lineId}`, {
        method: 'PATCH',
        body: JSON.stringify(patch),
      })
      setSaveState('SAVED')
      setLastSavedAt(new Date().toLocaleTimeString())
      await refreshQuoteDetails(currentQuoteId)
    } catch (error: any) {
      setSaveState('DIRTY')
      setStatus(error.message)
    }
  }

  async function removeLineItem(lineId: string) {
    if (!currentQuoteId) return
    try {
      setSaveState('SAVING')
      await request(`/api/quotes/${currentQuoteId}/line-items/${lineId}`, { method: 'DELETE' })
      setStatus('Line removed')
      setSaveState('SAVED')
      setLastSavedAt(new Date().toLocaleTimeString())
      await refreshQuoteDetails(currentQuoteId)
    } catch (error: any) {
      setSaveState('DIRTY')
      setStatus(error.message)
    }
  }

  async function duplicateCurrentQuote() {
    if (!currentQuoteId || !currentQuote) return
    try {
      const duplicate = await request('/api/quotes', {
        method: 'POST',
        body: JSON.stringify({
          customer_external_id: `${quoteDraft.customer_external_id || 'Customer'} (Copy)`,
          currency: currentQuote.currency,
          region: currentQuote.region || quoteDraft.region,
          price_book_id: currentQuote.price_book_id,
        }),
      })
      for (const line of quoteLines) {
        await request(`/api/quotes/${duplicate.id}/line-items`, {
          method: 'POST',
          body: JSON.stringify({
            commercial_item_id: line.commercial_item_id,
            quantity: line.quantity,
            discount_pct: line.discount_pct,
          }),
        })
      }
      setCurrentQuoteId(duplicate.id)
      await refreshQuoteDetails(duplicate.id)
      setStatus('Quote duplicated')
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function archiveCurrentQuote() {
    if (!currentQuoteId) return
    try {
      await request(`/api/quotes/${currentQuoteId}/status`, {
        method: 'POST',
        body: JSON.stringify({ target_status: 'ARCHIVED' }),
      })
      setStatus('Quote archived')
      await refreshCore()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  function toggleFavorite(itemId: string) {
    setFavoriteItemIds((prev) => (prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [itemId, ...prev]))
  }

  function toggleLineExpanded(lineId: string) {
    setExpandedLineIds((prev) => (prev.includes(lineId) ? prev.filter((id) => id !== lineId) : [...prev, lineId]))
  }

  async function selectPriceBookForQuote(nextBookId: string) {
    const nextBook = priceBooks.find((b) => b.id === nextBookId)
    if (!nextBook) return
    if (currentQuoteId && quoteLines.length > 0) {
      const ok = window.confirm('Changing price book will trigger full recalculation of the quote. Continue?')
      if (!ok) return
    }
    setQuoteDraft((prev) => ({ ...prev, price_book_id: nextBookId, currency: nextBook.currency }))
    setSaveState('DIRTY')
  }

  function selectCurrencyForQuote(nextCurrency: string) {
    if (nextCurrency === quoteDraft.currency) return
    if (currentQuoteId && quoteLines.length > 0) {
      const ok = window.confirm('Currency change may introduce rounding differences across line items. Continue?')
      if (!ok) return
    }
    setQuoteDraft((prev) => ({ ...prev, currency: nextCurrency }))
    setSaveState('DIRTY')
  }

  function openPricingDrawer(lineId: string) {
    const line = quoteLines.find((ln) => ln.id === lineId)
    setSelectedExplainLineId(lineId)
    setSimQuantity(Number(line?.quantity || 1))
    setSimDiscount(Number(line?.discount_pct || 0))
    setPricingDrawerOpen(true)
  }

  function simulateNetPrice(explanation: any, quantity: number, discountPct: number) {
    if (!explanation) return 0
    const seed = explanation.simulation_seed || {}
    let baseUnit = Number(seed.base_unit || 0)
    const tiers = seed.tiers || []
    if (tiers.length > 0) {
      for (const tier of tiers) {
        const lower = Number(tier.min || 0)
        const upper = tier.max == null ? null : Number(tier.max)
        const upperOk = upper == null || quantity <= upper
        if (quantity >= lower && upperOk) {
          baseUnit = Number(tier.price || baseUnit)
          break
        }
      }
    }
    const maxDiscount = seed.max_discount_pct == null ? null : Number(seed.max_discount_pct)
    const appliedDiscount = maxDiscount == null ? discountPct : Math.min(discountPct, maxDiscount)
    let unit = baseUnit * (1 - appliedDiscount / 100)
    if (seed.min_price != null) unit = Math.max(unit, Number(seed.min_price))
    return unit * quantity
  }

  async function escalateApprovalReminder() {
    if (!approvalState?.id) return
    try {
      await request(`/api/approvals/${approvalState.id}/remind`, { method: 'POST' })
      setStatus('Escalation reminder queued')
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function decisionAction(action: ApprovalAction) {
    const comment = (decisionComment || approvalComments || '').trim()
    if (action === 'REJECT' && comment.length === 0) {
      setStatus('Rejection reason is required')
      return
    }
    if (action === 'REQUEST_CHANGES' && comment.length === 0) {
      setStatus('Request changes reason is required')
      return
    }
    await requestApprovalAction(action, comment || (action === 'APPROVE' ? 'Approved in decision workspace' : 'Action taken'))
  }

  async function applyApprovalDiscountAdjustment() {
    if (!currentQuoteId || quoteLines.length === 0) {
      setStatus('No quote lines available for discount adjustment')
      return
    }
    const targetLine = quoteLines[0]
    await updateLineItem(targetLine.id, { discount_pct: decisionAdjustDiscount })
    setStatus('Discount adjusted for approval simulation path')
  }

  function estimateMarginAfterAdjustment() {
    if (!preview || quoteLines.length === 0) return null
    const first = quoteLines[0]
    const baseUnit = Number(first.list_price ?? first.unit_price ?? 0)
    const quantity = Number(first.quantity || 1)
    const adjustedNet = baseUnit * (1 - decisionAdjustDiscount / 100) * quantity
    const otherLinesNet = quoteLines.slice(1).reduce((acc, line) => acc + Number(line.net_price || 0), 0)
    const proposedTotal = adjustedNet + otherLinesNet
    const proposedMargin = proposedTotal > 0 ? ((proposedTotal * 0.28) / proposedTotal) * 100 : 0
    return { proposedTotal, proposedMargin }
  }

  async function submitForApproval() {
    if (!currentQuoteId) return
    try {
      const approval = await request(`/api/quotes/${currentQuoteId}/submit`, { method: 'POST' })
      setApprovalState(approval)
      const timeline = await request(`/api/approvals/${approval.id}/timeline`).catch(() => null)
      setApprovalTimeline(timeline?.timeline || [])
      setStatus('Quote submitted for approval')
      await refreshCore()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function requestApprovalAction(action: ApprovalAction, comments: string) {
    if (!approvalState?.id) {
      setStatus('No approval in progress')
      return
    }
    try {
      const updated = await request(`/api/approvals/${approvalState.id}/actions`, {
        method: 'POST',
        body: JSON.stringify({ action, comments }),
      })
      setApprovalState(updated)
      const timeline = await request(`/api/approvals/${approvalState.id}/timeline`).catch(() => null)
      setApprovalTimeline(timeline?.timeline || [])
      setStatus(`Approval action submitted: ${action}`)
      await refreshCore()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createRevision(reason: string) {
    if (!currentQuoteId) return
    try {
      await request(`/api/quotes/${currentQuoteId}/revisions`, {
        method: 'POST',
        body: JSON.stringify({ change_reason: reason }),
      })
      setStatus('Revision saved')
      await refreshQuoteDetails(currentQuoteId)
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function queuePdf() {
    if (!currentQuoteId) return
    try {
      const job = await request(`/api/async/quote-pdf/${currentQuoteId}`, { method: 'POST' })
      setLastPdfJob(job)
      setStatus('PDF generation queued')
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  function diffSummary() {
    if (revisions.length < 2) return 'Not enough revisions for diff view.'
    const latest = revisions[revisions.length - 1]?.snapshot_json
    const previous = revisions[revisions.length - 2]?.snapshot_json
    const latestLines = latest?.lines?.length ?? 0
    const prevLines = previous?.lines?.length ?? 0
    return `Lines changed from ${prevLines} to ${latestLines}`
  }

  function buildRevisionDiff(): RevisionDiffRow[] {
    if (revisions.length < 2) return []
    const latest = revisions[revisions.length - 1]?.snapshot_json?.lines || []
    const previous = revisions[revisions.length - 2]?.snapshot_json?.lines || []

    const lineLabel = (line: any) => {
      const qty = Number(line?.quantity ?? 0)
      const disc = Number(line?.discount_pct ?? 0)
      const net = Number(line?.net_price ?? line?.pricing_snapshot_json?.net_total ?? 0)
      return `qty=${qty} disc=${disc}% net=${net.toFixed(2)}`
    }

    const lineKey = (line: any) => String(line?.commercial_item_id || line?.line_no || line?.id)
    const prevMap = new Map<string, any>(previous.map((line: any) => [lineKey(line), line]))
    const nextMap = new Map<string, any>(latest.map((line: any) => [lineKey(line), line]))
    const allKeys = Array.from(new Set([...prevMap.keys(), ...nextMap.keys()]))

    const rows: RevisionDiffRow[] = []
    for (const key of allKeys) {
      const before = prevMap.get(key)
      const after = nextMap.get(key)
      if (!before && after) {
        rows.push({ key, change: 'ADDED', before: '-', after: lineLabel(after) })
      } else if (before && !after) {
        rows.push({ key, change: 'REMOVED', before: lineLabel(before), after: '-' })
      } else if (before && after) {
        const beforeLabel = lineLabel(before)
        const afterLabel = lineLabel(after)
        if (beforeLabel !== afterLabel) {
          rows.push({ key, change: 'MODIFIED', before: beforeLabel, after: afterLabel })
        }
      }
    }
    return rows
  }

  async function createAndPublishPriceBook(e: FormEvent) {
    e.preventDefault()
    try {
      const book = await request('/api/price-books', { method: 'POST', body: JSON.stringify(newPriceBook) })
      await request(`/api/price-books/${book.id}/publish`, { method: 'POST' })
      setPricingConfig((prev) => ({ ...prev, price_book_id: book.id, currency: newPriceBook.currency }))
      setStatus(`Price book ${book.name} created and published`)
      await refreshCore()
      await loadFunctionData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function updatePriceBookDetails(e: FormEvent) {
    e.preventDefault()
    if (!priceBookEditDraft) return
    try {
      await request(`/api/price-books/${priceBookEditDraft.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          name: priceBookEditDraft.name,
          currency: priceBookEditDraft.currency,
        }),
      })
      setPriceBookEditDraft(null)
      setStatus('Price book updated')
      await refreshCore()
      await loadFunctionData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function deletePriceBook(priceBookId: string) {
    const ok = window.confirm('Delete this price book? This cannot be undone.')
    if (!ok) return
    try {
      await request(`/api/price-books/${priceBookId}`, { method: 'DELETE' })
      setStatus('Price book deleted')
      if (pricingConfig.price_book_id === priceBookId) {
        setPricingConfig((prev) => ({ ...prev, price_book_id: '' }))
      }
      await refreshCore()
      await loadFunctionData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function savePricingConfiguration(e: FormEvent) {
    e.preventDefault()
    try {
      const tiers = JSON.parse(pricingConfig.tiers_json)
      await request('/api/price-books/entries', {
        method: 'POST',
        body: JSON.stringify({
          price_book_id: pricingConfig.price_book_id,
          commercial_item_id: pricingConfig.commercial_item_id,
          pricing_model: pricingConfig.pricing_model,
          base_price: pricingConfig.base_price,
          min_price: pricingConfig.min_price,
          max_discount_pct: pricingConfig.max_discount_pct,
          region: pricingConfig.region,
          currency: pricingConfig.currency,
          metadata_json: { tiers },
        }),
      })
      setStatus('Pricing configuration saved')
      await loadFunctionData()
    } catch (error: any) {
      setStatus(`Failed to save pricing config: ${error.message}`)
    }
  }

  async function runPricingSimulation() {
    if (!pricingConfig.price_book_id || !pricingConfig.commercial_item_id) {
      setStatus('Select price book and item before simulation')
      return
    }
    try {
      const quote = await request('/api/quotes', {
        method: 'POST',
        body: JSON.stringify({
          customer_external_id: 'SIMULATION',
          currency: pricingConfig.currency,
          region: pricingConfig.region,
          price_book_id: pricingConfig.price_book_id,
        }),
      })
      await request(`/api/quotes/${quote.id}/line-items`, {
        method: 'POST',
        body: JSON.stringify({
          commercial_item_id: pricingConfig.commercial_item_id,
          quantity: simInput.quantity,
          discount_pct: simInput.discount_pct,
        }),
      })
      const result = await request(`/api/quotes/${quote.id}/price-preview`, { method: 'POST' })
      setSimResult(result)
      setStatus('Simulation complete')
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createCatalogItem(e: FormEvent) {
    e.preventDefault()
    try {
      await request('/api/catalog/items', {
        method: 'POST',
        body: JSON.stringify({ ...catalogDraft, versionable: true }),
      })
      setCatalogDraft({ item_code: '', name: '', item_type: 'SERVICE' })
      setStatus('Catalog item created')
      await refreshCore()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createRule(e: FormEvent) {
    e.preventDefault()
    try {
      const payload = {
        name: ruleDraft.name,
        rule_type: ruleDraft.rule_type,
        priority: ruleDraft.priority,
        dsl_json: { when: { [ruleDraft.when_key]: ruleDraft.when_value }, then: { [ruleDraft.then_key]: ruleDraft.then_value } },
      }
      await request('/api/rules', { method: 'POST', body: JSON.stringify(payload) })
      setStatus('Rule created')
      await loadFunctionData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function validateRule() {
    try {
      const payload = {
        name: ruleDraft.name,
        rule_type: ruleDraft.rule_type,
        priority: ruleDraft.priority,
        dsl_json: { when: { [ruleDraft.when_key]: ruleDraft.when_value }, then: { [ruleDraft.then_key]: ruleDraft.then_value } },
      }
      const result = await request('/api/rules/validate', { method: 'POST', body: JSON.stringify(payload) })
      setStatus(result.valid ? 'Rule is valid' : `Rule invalid: ${result.issues?.join(', ')}`)
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function createApprovalPolicy(e: FormEvent) {
    e.preventDefault()
    try {
      await request('/api/approval-policies', {
        method: 'POST',
        body: JSON.stringify({
          name: approvalPolicyDraft.name,
          conditions: {
            min_grand_total: approvalPolicyDraft.min_grand_total,
            max_margin_pct: approvalPolicyDraft.max_margin_pct,
          },
          route: { levels: approvalPolicyDraft.levels },
        }),
      })
      setStatus('Approval policy saved')
      await loadFunctionData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function inviteUser(e: FormEvent) {
    e.preventDefault()
    if (!inviteEmail) return
    try {
      await request('/api/admin/users', {
        method: 'POST',
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      })
      setInviteEmail('')
      setStatus('User invited')
      await loadAdminData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function toggleUser(userId: string) {
    try {
      await request(`/api/admin/users/${userId}/toggle`, { method: 'PATCH' })
      setStatus('User state updated')
      await loadAdminData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function togglePermission(role: string, perm: string) {
    const next = {
      ...roleMatrix,
      [role]: {
        ...roleMatrix[role],
        [perm]: !roleMatrix[role][perm],
      },
    }
    setRoleMatrix(next)
    try {
      await request('/api/admin/role-matrix', {
        method: 'PUT',
        body: JSON.stringify({ matrix: next }),
      })
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function bulkUpdateRateCards() {
    try {
      const updated = await request('/api/admin/rate-cards/bulk-update', {
        method: 'POST',
        body: JSON.stringify({ pct: rateBulkPct }),
      })
      setRateCardRows(updated)
      setStatus(`Rate cards updated by ${rateBulkPct}%`)
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function saveOrgSettings() {
    try {
      await request('/api/admin/org-settings', {
        method: 'PUT',
        body: JSON.stringify(orgSettings),
      })
      setStatus('Organization settings saved')
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function toggleFeatureFlag(flag: string) {
    const next = { ...featureFlags, [flag]: !featureFlags[flag as keyof typeof featureFlags] }
    setFeatureFlags(next)
    try {
      await request('/api/admin/feature-flags', {
        method: 'PUT',
        body: JSON.stringify({ flags: next }),
      })
      setStatus('Feature flags updated')
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  async function addRateCardRow(e: FormEvent) {
    e.preventDefault()
    try {
      await request('/api/admin/rate-cards', {
        method: 'POST',
        body: JSON.stringify(rateCardDraft),
      })
      setRateCardDraft({ role: '', delivery: 'REMOTE', rate: 100, region: 'US', effective: '2026-01-01' })
      setStatus('Rate card row added')
      await loadAdminData()
    } catch (error: any) {
      setStatus(error.message)
    }
  }

  const adminSetupSteps: Array<{ id: AdminSetupView; title: string; icon: string; hint: string }> = [
    { id: 'ORG', title: 'Tenant Setup', icon: 'TS', hint: 'Define legal entity details, timezone, fiscal cycle, and branding defaults.' },
    { id: 'USERS', title: 'Users & Roles', icon: 'UR', hint: 'Invite users and assign permission roles before policy rollout.' },
    { id: 'ACCESS', title: 'Access Control', icon: 'AC', hint: 'Configure role-to-permission controls for secure operations.' },
    { id: 'GOVERNANCE', title: 'Governance', icon: 'GV', hint: 'Monitor feature flags, usage health, and governance metrics.' },
    { id: 'DASHBOARD', title: 'Control Tower', icon: 'CT', hint: 'Use a commercial operations cockpit for setup verification.' },
    { id: 'ACCOUNTS', title: 'Accounts', icon: 'AM', hint: 'Create and manage customer accounts with ownership and segmentation.' },
    { id: 'CONTACTS', title: 'Contacts', icon: 'CN', hint: 'Manage customer contacts and assign each to the right account.' },
    { id: 'OPPORTUNITIES', title: 'Leads & Opportunities', icon: 'LO', hint: 'Track lead and opportunity records tied to customer accounts.' },
    { id: 'PIPELINE', title: 'Pipeline & Reports', icon: 'PR', hint: 'Monitor stage flow, weighted pipeline, and conversion indicators.' },
    { id: 'PRICEBOOKS', title: 'Pricing Simulator', icon: 'PS', hint: 'Create and test price books with simulated commercial outcomes.' },
    { id: 'CATALOG', title: 'Catalog', icon: 'CG', hint: 'Define commercial items used by pricing and quoting workflows.' },
    { id: 'RULES', title: 'Rules Builder', icon: 'RB', hint: 'Translate pricing and approval guardrails into executable rules.' },
    { id: 'RATECARDS', title: 'Rate Cards', icon: 'RC', hint: 'Maintain labor rates by role, region, and delivery model.' },
    { id: 'APPROVAL_POLICIES', title: 'Approval Policies', icon: 'AP', hint: 'Set escalation levels and margin/threshold policy checks.' },
  ]

  function openAdminSetupView(view: AdminSetupView) {
    setAdminSetupView(view)
    if (view === 'ORG' || view === 'USERS' || view === 'ACCESS' || view === 'GOVERNANCE') {
      setAdminModule(view)
      return
    }
    setFunctionModule(view)
  }

  function openFunctionSetup(module: FunctionModule) {
    if (isAdmin) {
      openAdminSetupView(module)
      return
    }
    setFunctionModule(module)
  }

  const activeSetupStep = adminSetupSteps.find((step) => step.id === adminSetupView) || adminSetupSteps[0]
  const showFnDashboard = canUseFunctionalSetup && ((!isAdmin && functionModule === 'DASHBOARD') || (isAdmin && adminSetupView === 'DASHBOARD'))
  const showFnAccounts = canUseMiniCrm && ((!isAdmin && functionModule === 'ACCOUNTS') || (isAdmin && adminSetupView === 'ACCOUNTS'))
  const showFnContacts = canUseMiniCrm && ((!isAdmin && functionModule === 'CONTACTS') || (isAdmin && adminSetupView === 'CONTACTS'))
  const showFnOpportunities = canUseMiniCrm && ((!isAdmin && functionModule === 'OPPORTUNITIES') || (isAdmin && adminSetupView === 'OPPORTUNITIES'))
  const showFnPipeline = canUseMiniCrm && ((!isAdmin && functionModule === 'PIPELINE') || (isAdmin && adminSetupView === 'PIPELINE'))
  const showFnPriceBooks = canUseFunctionalSetup && ((!isAdmin && functionModule === 'PRICEBOOKS') || (isAdmin && adminSetupView === 'PRICEBOOKS'))
  const showFnCatalog = canUseFunctionalSetup && ((!isAdmin && functionModule === 'CATALOG') || (isAdmin && adminSetupView === 'CATALOG'))
  const showFnRules = canUseFunctionalSetup && ((!isAdmin && functionModule === 'RULES') || (isAdmin && adminSetupView === 'RULES'))
  const showFnRateCards = canUseFunctionalSetup && ((!isAdmin && functionModule === 'RATECARDS') || (isAdmin && adminSetupView === 'RATECARDS'))
  const showFnApprovalPolicies = canUseFunctionalSetup && ((!isAdmin && functionModule === 'APPROVAL_POLICIES') || (isAdmin && adminSetupView === 'APPROVAL_POLICIES'))

  if (!token) {
    return (
      <div className="login-shell">
        <div className="ambient-orb ambient-a" />
        <div className="ambient-orb ambient-b" />

        <main className="login-panel">
          <form className="login-form" onSubmit={signIn}>
            <p className="eyebrow">Secure Access</p>
            <h2>Smart Pricing Platform Login</h2>

            <label>
              Work Email
              <input type="email" placeholder="name@company.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label>
              Password
              <input type="password" placeholder="Enter password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </label>
            <label>
              Tenant ID
              <input type="text" value={tenantId} onChange={(e) => setTenantId(e.target.value)} required />
            </label>
            <div className="action-row">
              <button type="submit" disabled={loading}>{loading ? 'Please wait...' : 'Sign In'}</button>
              <button type="button" className="secondary" onClick={ssoSignIn} disabled={loading}>Continue with SSO</button>
            </div>
            {status && <p className="status">{status}</p>}
          </form>
        </main>
      </div>
    )
  }

  return (
    <div className="workspace-shell app-shell">
      <header className="workspace-head">
        <div>
          <p className="eyebrow">{workspaceTitle}</p>
          <h1>{workspaceTitle}</h1>
          <p>{workspaceSubtitle}</p>
        </div>
        <div className="header-actions">
          <button className="secondary" onClick={() => refreshCore()} disabled={refreshingCore}>{refreshingCore ? 'Refreshing...' : 'Refresh'}</button>
          <button onClick={signOut}>Sign Out</button>
        </div>
      </header>

      {isAdmin ? (
        <section className="setup-shell">
          <div className="setup-head">
            <p className="eyebrow">Guided Admin Setup</p>
            <h2>{activeSetupStep.title}</h2>
            <p>{activeSetupStep.hint}</p>
          </div>
          <div className="setup-tabs" role="tablist" aria-label="Admin setup flow">
            {adminSetupSteps
              .filter((step) => {
                const adminCore = ['ORG', 'USERS', 'ACCESS', 'GOVERNANCE'].includes(step.id)
                const crmCore = ['ACCOUNTS', 'CONTACTS', 'OPPORTUNITIES', 'PIPELINE'].includes(step.id)
                if (adminCore) return true
                if (crmCore) return canUseMiniCrm
                return canUseFunctionalSetup
              })
              .map((step, index) => (
                <button
                  key={step.id}
                  className={adminSetupView === step.id ? 'active' : ''}
                  onClick={() => openAdminSetupView(step.id)}
                  title={step.hint}
                  aria-label={`${index + 1}. ${step.title}. ${step.hint}`}
                >
                  <span className="setup-icon" aria-hidden="true">{step.icon}</span>
                  <span>{index + 1}. {step.title}</span>
                </button>
              ))}
          </div>
        </section>
      ) : (
        <section className="module-tabs">
          {canUseMiniCrm && (
          <>
            <button className={functionModule === 'ACCOUNTS' ? 'active' : ''} onClick={() => setFunctionModule('ACCOUNTS')}>Accounts</button>
            <button className={functionModule === 'CONTACTS' ? 'active' : ''} onClick={() => setFunctionModule('CONTACTS')}>Contacts</button>
            <button className={functionModule === 'OPPORTUNITIES' ? 'active' : ''} onClick={() => setFunctionModule('OPPORTUNITIES')}>Leads & Opportunities</button>
            <button className={functionModule === 'PIPELINE' ? 'active' : ''} onClick={() => setFunctionModule('PIPELINE')}>Pipeline</button>
          </>
          )}
          {canUseFunctionalSetup && (
          <>
            <button className={functionModule === 'DASHBOARD' ? 'active' : ''} onClick={() => setFunctionModule('DASHBOARD')}>Control Tower</button>
            <button className={functionModule === 'PRICEBOOKS' ? 'active' : ''} onClick={() => setFunctionModule('PRICEBOOKS')}>Pricing Simulator</button>
            <button className={functionModule === 'CATALOG' ? 'active' : ''} onClick={() => setFunctionModule('CATALOG')}>Catalog</button>
            <button className={functionModule === 'RULES' ? 'active' : ''} onClick={() => setFunctionModule('RULES')}>Rules Builder</button>
            <button className={functionModule === 'RATECARDS' ? 'active' : ''} onClick={() => setFunctionModule('RATECARDS')}>Rate Cards</button>
            <button className={functionModule === 'APPROVAL_POLICIES' ? 'active' : ''} onClick={() => setFunctionModule('APPROVAL_POLICIES')}>Approval Policies</button>
          </>
        )}
        {!isAdmin && (
          <>
            <button className={endUserModule === 'DASHBOARD' ? 'active' : ''} onClick={() => setEndUserModule('DASHBOARD')}>Dashboard</button>
            <button className={endUserModule === 'QUOTE_CREATE' ? 'active' : ''} onClick={() => setEndUserModule('QUOTE_CREATE')}>Quote Creation</button>
            <button className={endUserModule === 'REVISIONS' ? 'active' : ''} onClick={() => setEndUserModule('REVISIONS')}>Revisions</button>
            <button className={endUserModule === 'APPROVALS' ? 'active' : ''} onClick={() => setEndUserModule('APPROVALS')}>Approvals</button>
            <button className={endUserModule === 'OUTPUT' ? 'active' : ''} onClick={() => setEndUserModule('OUTPUT')}>Output & Sharing</button>
          </>
          )}
        </section>
      )}

      {isAdmin && adminSetupView === 'ORG' && adminModule === 'ORG' && (
        <main className="workspace-grid two-col page-admin-org">
          <section className="card-panel">
            <h2><span className="title-icon" aria-hidden="true">TS</span>Organization Profile</h2>
            <div className="stack">
              <label>
                Organization Name
                <input
                  value={orgSettings.name}
                  onChange={(e) => setOrgSettings({ ...orgSettings, name: e.target.value })}
                  placeholder="Default Organization"
                  title="Official name used in policy and quote templates."
                />
                <small className="field-hint">Use your legal or primary commercial entity name.</small>
              </label>
              <div className="inline-fields">
                <label>
                  Region
                  <input value={orgSettings.region} onChange={(e) => setOrgSettings({ ...orgSettings, region: e.target.value })} placeholder="US" title="Primary operating region code." />
                  <small className="field-hint">Use a short geo code like `US`, `EU`, or `APAC`.</small>
                </label>
                <label>
                  Timezone
                  <input value={orgSettings.timezone} onChange={(e) => setOrgSettings({ ...orgSettings, timezone: e.target.value })} placeholder="America/New_York" title="Default timezone used for policies and approvals." />
                  <small className="field-hint">Use an IANA timezone format, for example `America/New_York`.</small>
                </label>
              </div>
              <div className="inline-fields">
                <label>
                  Default Currency
                  <input value={orgSettings.default_currency} onChange={(e) => setOrgSettings({ ...orgSettings, default_currency: e.target.value })} placeholder="USD" title="Default quote and pricing currency." />
                  <small className="field-hint">Use an ISO currency code like `USD` or `EUR`.</small>
                </label>
                <label>
                  Fiscal Year Start
                  <input type="date" value={orgSettings.fiscal_year_start} onChange={(e) => setOrgSettings({ ...orgSettings, fiscal_year_start: e.target.value })} title="Start date for fiscal and policy reporting periods." />
                  <small className="field-hint">Pick the first date of your financial year.</small>
                </label>
              </div>
              <label>
                Tax Behavior
                <select value={orgSettings.tax_behavior} onChange={(e) => setOrgSettings({ ...orgSettings, tax_behavior: e.target.value })} title="Choose whether tax is calculated by the engine or display-only.">
                  <option value="DISPLAY_ONLY">DISPLAY_ONLY</option>
                  <option value="CALCULATED">CALCULATED</option>
                </select>
                <small className="field-hint">`CALCULATED` applies computed tax. `DISPLAY_ONLY` keeps tax informational.</small>
              </label>
            </div>
          </section>
          <section className="card-panel">
            <h2><span className="title-icon" aria-hidden="true">BR</span>Branding & Financial Controls</h2>
            <div className="stack">
              <label>
                Logo URL
                <input value={orgSettings.logo_url} onChange={(e) => setOrgSettings({ ...orgSettings, logo_url: e.target.value })} placeholder="https://cdn.example.com/logo.svg" title="Public URL for organization logo in documents and UI." />
                <small className="field-hint">Use an HTTPS URL to an image asset (`.svg`, `.png`, or `.jpg`).</small>
              </label>
              <label>
                Primary Color
                <input value={orgSettings.primary_color} onChange={(e) => setOrgSettings({ ...orgSettings, primary_color: e.target.value })} placeholder="#0f8f7a" title="Primary brand accent used across admin workspace UI." />
                <small className="field-hint">Use a HEX value like `#0f8f7a` for consistent branding.</small>
              </label>
              <button onClick={saveOrgSettings} title="Save and apply tenant setup values.">Save Organization Settings</button>
            </div>
          </section>
        </main>
      )}

      {isAdmin && adminSetupView === 'USERS' && adminModule === 'USERS' && (
        <main className="workspace-grid two-col page-admin-users">
          <section className="card-panel">
            <h2>Invite User</h2>
            <form className="stack" onSubmit={inviteUser}>
              <input type="email" value={inviteEmail} onChange={(e) => setInviteEmail(e.target.value)} placeholder="user@company.com" required />
              <select value={inviteRole} onChange={(e) => setInviteRole(e.target.value as LocalUser['role'])}>
                <option value="ADMIN">ADMIN</option>
                <option value="SALES">SALES</option>
                <option value="OPERATIONS">OPERATIONS</option>
                <option value="FINANCE">FINANCE</option>
                <option value="DELIVERY">DELIVERY</option>
                <option value="LEADERSHIP">LEADERSHIP</option>
                <option value="CUSTOM">CUSTOM</option>
              </select>
              <button type="submit">Invite / Add User</button>
            </form>
          </section>
          <section className="card-panel">
            <h2>User Directory</h2>
            <ul>
              {users.map((u) => (
                <li key={u.id} className="list-row">
                  <span>{u.email} ({u.role})</span>
                  <button className="secondary" onClick={() => toggleUser(u.id)}>{u.active ? 'Disable' : 'Enable'}</button>
                </li>
              ))}
            </ul>
            <h3>Recent Role Change Audit</h3>
            <ul>
              {auditEvents.slice(0, 6).map((evt, i) => (
                <li key={`${evt.id}-${i}`}>{evt.action || evt.entity_type} | {evt.created_at}</li>
              ))}
            </ul>
          </section>
        </main>
      )}

      {isAdmin && adminSetupView === 'ACCESS' && adminModule === 'ACCESS' && (
        <main className="workspace-grid one-col page-admin-access">
          <section className="card-panel">
            <h2>Role Permission Matrix</h2>
            <div className="matrix-grid">
              {Object.entries(roleMatrix).map(([role, perms]) => (
                <div key={role} className="matrix-col">
                  <h3>{role}</h3>
                  {Object.entries(perms).map(([perm, enabled]) => (
                    <label key={perm} className="matrix-toggle">
                      <span>{perm}</span>
                      <input type="checkbox" checked={enabled} onChange={() => togglePermission(role, perm)} />
                    </label>
                  ))}
                </div>
              ))}
            </div>
          </section>
        </main>
      )}

      {isAdmin && adminSetupView === 'GOVERNANCE' && adminModule === 'GOVERNANCE' && (
        <main className="workspace-grid two-col page-admin-governance">
          <section className="card-panel">
            <h2>Tenant Governance Snapshot</h2>
            <div className="kpi-strip">
              <div><strong>Users</strong><span>{users.length}</span></div>
              <div><strong>Quote Volume</strong><span>{metrics?.total_quotes ?? 0}</span></div>
              <div><strong>Finalized</strong><span>{metrics?.finalized_quotes ?? 0}</span></div>
              <div><strong>Req Count</strong><span>{obsMetrics?.request_count ?? 0}</span></div>
            </div>
            <h3>Feature Flags</h3>
            <div className="stack">
              {Object.entries(featureFlags).map(([key, value]) => (
                <label key={key} className="list-row">
                  <span>{key}</span>
                  <input type="checkbox" checked={value} onChange={() => { void toggleFeatureFlag(key) }} />
                </label>
              ))}
            </div>
          </section>
          <section className="card-panel">
            <h2>Integration & Workflow Health</h2>
            <p>Failures: {(obsMetrics?.status_codes?.['500'] ?? 0) + (obsMetrics?.status_codes?.['400'] ?? 0)}</p>
            <p>Pending Approvals: {metrics?.pending_approvals ?? 0}</p>
            <button onClick={() => setStatus('Governance controls saved')}>Apply Governance Settings</button>
          </section>
        </main>
      )}

      {showFnDashboard && (
        <main className="workspace-grid one-col function-admin-dashboard page-fn-dashboard">
          <section className="card-panel function-hero">
            <div>
              <p className="eyebrow">Function Admin Control Tower</p>
              <h2>Pricing, Rules, Access, and Deal Operations</h2>
              <p>
                Operational cockpit for commercial governance. Manage price books, policy controls, user permissions,
                and live quote flow from one place.
              </p>
            </div>
            <div className="kpi-strip">
              <div><strong>Price Books</strong><span>{priceBooks.length}</span></div>
              <div><strong>Rules</strong><span>{rules.length}</span></div>
              <div><strong>Approval Policies</strong><span>{approvalPolicies.length}</span></div>
              <div><strong>Quotes</strong><span>{quotes.length}</span></div>
            </div>
          </section>

          <section className="workspace-grid two-col">
            <section className="card-panel admin-table-card">
              <div className="section-head">
                <h3>Price Books</h3>
                <div className="inline-actions">
                  <button className="secondary" onClick={() => openFunctionSetup('PRICEBOOKS')} title="Open price book setup workspace.">Open Pricing Studio</button>
                </div>
              </div>
              <form className="inline-fields" onSubmit={createAndPublishPriceBook}>
                <input
                  value={newPriceBook.name}
                  onChange={(e) => setNewPriceBook({ ...newPriceBook, name: e.target.value })}
                  placeholder="New price book name"
                  required
                />
                <div className="inline-fields">
                  <input
                    value={newPriceBook.currency}
                    onChange={(e) => setNewPriceBook({ ...newPriceBook, currency: e.target.value })}
                    placeholder="Currency"
                    required
                  />
                  <button type="submit">Add Price Book</button>
                </div>
              </form>

              {priceBookEditDraft && (
                <form className="inline-fields" onSubmit={updatePriceBookDetails}>
                  <input
                    value={priceBookEditDraft.name}
                    onChange={(e) => setPriceBookEditDraft({ ...priceBookEditDraft, name: e.target.value })}
                    required
                  />
                  <div className="inline-fields">
                    <input
                      value={priceBookEditDraft.currency}
                      onChange={(e) => setPriceBookEditDraft({ ...priceBookEditDraft, currency: e.target.value })}
                      required
                    />
                    <div className="inline-actions">
                      <button type="submit">Save</button>
                      <button type="button" className="secondary" onClick={() => setPriceBookEditDraft(null)}>Cancel</button>
                    </div>
                  </div>
                </form>
              )}

              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Currency</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {priceBooks.map((book) => (
                      <tr key={book.id}>
                        <td>{book.name}</td>
                        <td>{book.currency}</td>
                        <td><span className={`status-badge ${book.status}`}>{book.status}</span></td>
                        <td>
                          <div className="inline-actions">
                            <button
                              type="button"
                              className="secondary"
                              onClick={() => {
                                setPricingConfig((prev) => ({ ...prev, price_book_id: book.id, currency: book.currency }))
                                openFunctionSetup('PRICEBOOKS')
                              }}
                            >
                              View
                            </button>
                            <button
                              type="button"
                              className="secondary"
                              onClick={() => setPriceBookEditDraft({ id: book.id, name: book.name, currency: book.currency })}
                            >
                              Edit
                            </button>
                            <button type="button" className="secondary" onClick={() => void deletePriceBook(book.id)}>Delete</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {priceBooks.length === 0 && (
                      <tr>
                        <td colSpan={4}>No price books yet.</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="card-panel admin-table-card">
              <div className="section-head">
                <h3>Rules & Approval Policies</h3>
                <div className="inline-actions">
                  <button className="secondary" onClick={() => openFunctionSetup('RULES')} title="Open rules setup workspace.">Rules Builder</button>
                  <button className="secondary" onClick={() => openFunctionSetup('APPROVAL_POLICIES')} title="Open approval policy setup workspace.">Policies</button>
                </div>
              </div>
              <div className="split-half">
                <div>
                  <h4>Rules</h4>
                  <ul>
                    {rules.slice(0, 6).map((rule) => (
                      <li key={rule.id} className="list-row">
                        <span>{rule.name}</span>
                        <span>{rule.rule_type} | P{rule.priority}</span>
                      </li>
                    ))}
                    {rules.length === 0 && <li className="list-row"><span>No rules configured.</span></li>}
                  </ul>
                </div>
                <div>
                  <h4>Approval Policies</h4>
                  <ul>
                    {approvalPolicies.slice(0, 6).map((policy) => (
                      <li key={policy.id} className="list-row">
                        <span>{policy.name}</span>
                        <span>L{policy.route?.levels ?? 1} | Min {(policy.conditions?.min_grand_total ?? 0).toLocaleString()}</span>
                      </li>
                    ))}
                    {approvalPolicies.length === 0 && <li className="list-row"><span>No approval policies configured.</span></li>}
                  </ul>
                </div>
              </div>
            </section>
          </section>

          <section className="workspace-grid two-col">
            <section className="card-panel admin-table-card">
              <div className="section-head">
                <h3>Users & Roles</h3>
                <button className="secondary" onClick={() => setStatus('Admin access is required for invite/disable and role edits.')}>Manage in Admin Console</button>
              </div>
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Role</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((u) => (
                      <tr key={u.id}>
                        <td>{u.email}</td>
                        <td>{u.role}</td>
                        <td>{u.active ? 'Active' : 'Disabled'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="card-panel admin-table-card">
              <div className="section-head">
                <h3>Quotes by Status</h3>
                <button className="secondary" onClick={() => setStatus('Use a Normal User role for the full quote workspace.')}>Open Deal Workspace</button>
              </div>
              <div className="kpi-strip compact">
                <div><strong>Draft</strong><span>{metrics?.draft_quotes ?? 0}</span></div>
                <div><strong>Pending Approval</strong><span>{metrics?.pending_approvals ?? 0}</span></div>
                <div><strong>Finalized</strong><span>{metrics?.finalized_quotes ?? 0}</span></div>
                <div><strong>Total</strong><span>{metrics?.total_quotes ?? 0}</span></div>
              </div>
              <ul>
                {quotes.slice(0, 8).map((quote) => (
                  <li key={quote.id} className="list-row">
                    <span>{quote.quote_no} | {quote.status}</span>
                    <div className="inline-actions">
                      <span>${Number(quote.grand_total || 0).toFixed(2)}</span>
                      {quote.status === 'APPROVAL_PENDING' && <span className="panel-alert warn">Needs decision</span>}
                    </div>
                  </li>
                ))}
                {quotes.length === 0 && <li className="list-row"><span>No quotes available.</span></li>}
              </ul>
              {approvalPendingQuotes.length > 0 && (
                <p className="quote-meta">{approvalPendingQuotes.length} deals currently waiting in approval workflow.</p>
              )}
            </section>
          </section>
        </main>
      )}

      {showFnAccounts && (
        <main className="workspace-grid two-col page-fn-accounts">
          <section className="card-panel">
            <h2>Account Management</h2>
            <form className="stack" onSubmit={createAccount}>
              <input value={accountDraft.name} onChange={(e) => setAccountDraft({ ...accountDraft, name: e.target.value })} placeholder="Account name (required)" required />
              <div className="inline-fields">
                <input value={accountDraft.external_id} onChange={(e) => setAccountDraft({ ...accountDraft, external_id: e.target.value })} placeholder="External ID (optional)" />
                <input value={accountDraft.segment} onChange={(e) => setAccountDraft({ ...accountDraft, segment: e.target.value })} placeholder="Segment (SMB / Mid-Market / Enterprise)" />
              </div>
              <div className="inline-fields">
                <input value={accountDraft.industry} onChange={(e) => setAccountDraft({ ...accountDraft, industry: e.target.value })} placeholder="Industry (Healthcare, Finance...)" />
                <input value={accountDraft.owner} onChange={(e) => setAccountDraft({ ...accountDraft, owner: e.target.value })} placeholder="Account owner" />
              </div>
              <input value={accountDraft.website} onChange={(e) => setAccountDraft({ ...accountDraft, website: e.target.value })} placeholder="Website URL" />
              <button type="submit">Create Account</button>
            </form>
          </section>
          <section className="card-panel">
            <h2>Account Listing & Search</h2>
            <input value={accountSearch} onChange={(e) => setAccountSearch(e.target.value)} placeholder="Search by account name, external id, segment or industry" />
            <ul>
              {filteredAccounts.map((account) => (
                <li key={account.id} className="list-row">
                  <span>{account.name} | {account.external_id} | {account.segment}</span>
                  <div className="inline-actions">
                    <button className="secondary" onClick={() => setContactDraft((prev) => ({ ...prev, customer_id: account.id }))}>Add Contact</button>
                    <button className="secondary" onClick={() => setDealDraft((prev) => ({ ...prev, customer_id: account.id }))}>Add Deal</button>
                    <button className="secondary" onClick={() => void deleteAccount(account.id)}>Delete</button>
                  </div>
                </li>
              ))}
              {filteredAccounts.length === 0 && <li className="list-row"><span>No accounts found.</span></li>}
            </ul>
          </section>
        </main>
      )}

      {showFnContacts && (
        <main className="workspace-grid two-col page-fn-contacts">
          <section className="card-panel">
            <h2>Contact Management</h2>
            <form className="stack" onSubmit={createContactRecord}>
              <select value={contactDraft.customer_id} onChange={(e) => setContactDraft({ ...contactDraft, customer_id: e.target.value })} required>
                <option value="">Assign to Account</option>
                {crmAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
              </select>
              <div className="inline-fields">
                <input value={contactDraft.name} onChange={(e) => setContactDraft({ ...contactDraft, name: e.target.value })} placeholder="Contact name" required />
                <input type="email" value={contactDraft.email} onChange={(e) => setContactDraft({ ...contactDraft, email: e.target.value })} placeholder="Email (required)" required />
              </div>
              <div className="inline-fields">
                <input value={contactDraft.phone} onChange={(e) => setContactDraft({ ...contactDraft, phone: e.target.value })} placeholder="Phone" />
                <input value={contactDraft.title} onChange={(e) => setContactDraft({ ...contactDraft, title: e.target.value })} placeholder="Title" />
              </div>
              <input value={contactDraft.role} onChange={(e) => setContactDraft({ ...contactDraft, role: e.target.value })} placeholder="Role (Decision Maker / Finance / Legal...)" />
              <button type="submit">Save Contact</button>
            </form>
          </section>
          <section className="card-panel">
            <h2>Contacts Listing & Search</h2>
            <input value={contactSearch} onChange={(e) => setContactSearch(e.target.value)} placeholder="Search by contact name, email, or title" />
            <ul>
              {filteredContacts.map((contact) => (
                <li key={contact.id} className="list-row">
                  <span>
                    {contact.name} | {contact.email} | {(crmAccounts.find((account) => account.id === contact.customer_id)?.name) || 'Unknown Account'}
                  </span>
                  <button className="secondary" onClick={() => void deleteContactRecord(contact.id)}>Delete</button>
                </li>
              ))}
              {filteredContacts.length === 0 && <li className="list-row"><span>No contacts found.</span></li>}
            </ul>
          </section>
        </main>
      )}

      {showFnOpportunities && (
        <main className="workspace-grid two-col page-fn-opportunities">
          <section className="card-panel">
            <h2>Lead / Opportunity Management</h2>
            <form className="stack" onSubmit={createDeal}>
              <select value={dealDraft.customer_id} onChange={(e) => setDealDraft({ ...dealDraft, customer_id: e.target.value })} required>
                <option value="">Assign to Account</option>
                {crmAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
              </select>
              <div className="inline-fields">
                <select
                  value={dealDraft.record_type}
                  onChange={(e) => {
                    const recordType = e.target.value as 'LEAD' | 'OPPORTUNITY'
                    const nextStages = recordType === 'LEAD' ? crmLifecycle.lead : crmLifecycle.opportunity
                    setDealDraft({ ...dealDraft, record_type: recordType, stage: nextStages[0] || 'NEW' })
                  }}
                >
                  <option value="LEAD">LEAD</option>
                  <option value="OPPORTUNITY">OPPORTUNITY</option>
                </select>
                <select value={dealDraft.stage} onChange={(e) => setDealDraft({ ...dealDraft, stage: e.target.value })}>
                  {(dealDraft.record_type === 'LEAD' ? crmLifecycle.lead : crmLifecycle.opportunity).map((stage) => (
                    <option key={stage} value={stage}>{stage}</option>
                  ))}
                </select>
              </div>
              <input value={dealDraft.name} onChange={(e) => setDealDraft({ ...dealDraft, name: e.target.value })} placeholder="Lead / Opportunity name" required />
              <div className="inline-fields">
                <input type="number" value={dealDraft.amount} onChange={(e) => setDealDraft({ ...dealDraft, amount: Number(e.target.value) })} placeholder="Deal amount" />
                <input type="number" value={dealDraft.probability_pct} onChange={(e) => setDealDraft({ ...dealDraft, probability_pct: Number(e.target.value) })} placeholder="Probability %" />
              </div>
              <div className="inline-fields">
                <input type="date" value={dealDraft.close_date} onChange={(e) => setDealDraft({ ...dealDraft, close_date: e.target.value })} />
                <input value={dealDraft.owner} onChange={(e) => setDealDraft({ ...dealDraft, owner: e.target.value })} placeholder="Owner" />
              </div>
              <button type="submit">Save Lead / Opportunity</button>
            </form>
          </section>
          <section className="card-panel">
            <h2>Lifecycle Board</h2>
            <div className="inline-fields">
              <input value={dealSearch} onChange={(e) => setDealSearch(e.target.value)} placeholder="Search deal name or stage" />
              <select value={dealTypeFilter} onChange={(e) => setDealTypeFilter(e.target.value as 'ALL' | 'LEAD' | 'OPPORTUNITY')}>
                <option value="ALL">ALL</option>
                <option value="LEAD">LEAD</option>
                <option value="OPPORTUNITY">OPPORTUNITY</option>
              </select>
            </div>
            <ul>
              {filteredDeals.map((deal) => {
                const stageOptions = deal.record_type === 'LEAD' ? crmLifecycle.lead : crmLifecycle.opportunity
                return (
                  <li key={deal.id} className="list-row">
                    <span>
                      {deal.record_type} | {deal.name} | {(crmAccounts.find((account) => account.id === deal.customer_id)?.name) || 'Unknown Account'} | ${Number(deal.amount || 0).toLocaleString()}
                    </span>
                    <div className="inline-actions">
                      <select value={deal.stage} onChange={(e) => { void moveDealStage(deal.id, e.target.value) }}>
                        {stageOptions.map((stage) => <option key={stage} value={stage}>{stage}</option>)}
                      </select>
                      <button
                        className="secondary"
                        onClick={() => {
                          setGuidedSelectedOpportunityId(deal.id)
                          setGuidedSelectedCustomerId(deal.customer_id)
                          setQuoteDraft((prev) => ({
                            ...prev,
                            customer_external_id: deal.customer_id,
                            customer_account_id: deal.customer_id,
                            opportunity_id: deal.id,
                          }))
                          setStatus(`Opportunity linked for next quote: ${deal.name}`)
                        }}
                      >
                        Use in Quote
                      </button>
                      <button className="secondary" onClick={() => void deleteDeal(deal.id)}>Delete</button>
                    </div>
                  </li>
                )
              })}
              {filteredDeals.length === 0 && <li className="list-row"><span>No leads/opportunities found.</span></li>}
            </ul>
          </section>
        </main>
      )}

      {showFnPipeline && (
        <main className="workspace-grid one-col page-fn-pipeline">
          <section className="card-panel">
            <h2>Sales Pipeline Dashboard & Reports</h2>
            <div className="kpi-strip">
              <div><strong>Accounts</strong><span>{crmPipeline?.accounts_total ?? crmAccounts.length}</span></div>
              <div><strong>Contacts</strong><span>{crmPipeline?.contacts_total ?? crmContacts.length}</span></div>
              <div><strong>Open Deals</strong><span>{crmPipeline?.open_deals ?? 0}</span></div>
              <div><strong>Win Rate</strong><span>{Number(crmPipeline?.win_rate_pct ?? 0).toFixed(2)}%</span></div>
            </div>
            <div className="kpi-strip">
              <div><strong>Total Pipeline</strong><span>${Number(crmPipeline?.total_pipeline_amount ?? 0).toLocaleString()}</span></div>
              <div><strong>Weighted Pipeline</strong><span>${Number(crmPipeline?.weighted_pipeline_amount ?? 0).toLocaleString()}</span></div>
              <div><strong>Leads</strong><span>{crmPipeline?.by_record_type?.LEAD ?? 0}</span></div>
              <div><strong>Opportunities</strong><span>{crmPipeline?.by_record_type?.OPPORTUNITY ?? 0}</span></div>
            </div>
            <h3>Stage Distribution</h3>
            <ul>
              {Object.entries(crmPipeline?.by_stage || {}).map(([stage, count]) => (
                <li key={stage} className="list-row"><span>{stage}</span><strong>{String(count)}</strong></li>
              ))}
              {Object.keys(crmPipeline?.by_stage || {}).length === 0 && <li className="list-row"><span>No stage data available yet.</span></li>}
            </ul>
            <h3>Top Accounts by Pipeline Value</h3>
            <ul>
              {(crmPipeline?.top_accounts || []).map((item: any) => (
                <li key={item.account_name} className="list-row"><span>{item.account_name}</span><strong>${Number(item.amount || 0).toLocaleString()}</strong></li>
              ))}
              {(crmPipeline?.top_accounts || []).length === 0 && <li className="list-row"><span>No account report data available yet.</span></li>}
            </ul>
          </section>
        </main>
      )}

      {showFnPriceBooks && (
        <main className="workspace-grid two-col page-fn-pricebooks">
          <section className="card-panel">
            <h2>Price Book Management</h2>
            <form className="stack" onSubmit={createAndPublishPriceBook}>
              <input value={newPriceBook.name} onChange={(e) => setNewPriceBook({ ...newPriceBook, name: e.target.value })} required />
              <input value={newPriceBook.currency} onChange={(e) => setNewPriceBook({ ...newPriceBook, currency: e.target.value })} required />
              <button type="submit">Create + Publish</button>
            </form>
            <h3>Version Compare (Baseline)</h3>
            <ul>{priceBooks.map((book) => <li key={book.id}>{book.name} | {book.currency} | {book.status}</li>)}</ul>
          </section>

          <section className="card-panel">
            <h2>Pricing Simulator</h2>
            <form className="stack" onSubmit={savePricingConfiguration}>
              <select value={pricingConfig.price_book_id} onChange={(e) => setPricingConfig({ ...pricingConfig, price_book_id: e.target.value })} required>
                <option value="">Select price book</option>
                {priceBooks.map((book) => <option key={book.id} value={book.id}>{book.name}</option>)}
              </select>
              <select value={pricingConfig.commercial_item_id} onChange={(e) => setPricingConfig({ ...pricingConfig, commercial_item_id: e.target.value })} required>
                <option value="">Select item</option>
                {catalogItems.map((item) => <option key={item.id} value={item.id}>{item.item_code} - {item.name}</option>)}
              </select>
              <select value={pricingConfig.pricing_model} onChange={(e) => setPricingConfig({ ...pricingConfig, pricing_model: e.target.value })}>
                <option>FIXED_PRICE</option>
                <option>PER_USER</option>
                <option>PER_UNIT</option>
                <option>TIERED</option>
                <option>USAGE_BASED</option>
              </select>
              <div className="inline-fields">
                <input type="number" value={pricingConfig.base_price} onChange={(e) => setPricingConfig({ ...pricingConfig, base_price: Number(e.target.value) })} />
                <input type="number" value={pricingConfig.min_price} onChange={(e) => setPricingConfig({ ...pricingConfig, min_price: Number(e.target.value) })} />
              </div>
              <div className="inline-fields">
                <input type="number" value={pricingConfig.max_discount_pct} onChange={(e) => setPricingConfig({ ...pricingConfig, max_discount_pct: Number(e.target.value) })} />
                <input value={pricingConfig.region} onChange={(e) => setPricingConfig({ ...pricingConfig, region: e.target.value })} />
              </div>
              <label>
                Tier JSON
                <textarea value={pricingConfig.tiers_json} onChange={(e) => setPricingConfig({ ...pricingConfig, tiers_json: e.target.value })} rows={4} />
              </label>
              <button type="submit">Save Configuration</button>
            </form>
            <div className="inline-fields">
              <input type="number" value={simInput.quantity} onChange={(e) => setSimInput({ ...simInput, quantity: Number(e.target.value) })} />
              <input type="number" value={simInput.discount_pct} onChange={(e) => setSimInput({ ...simInput, discount_pct: Number(e.target.value) })} />
            </div>
            <button onClick={runPricingSimulation}>Run Simulation</button>
            {simResult && (
              <div className="preview">
                <p>Subtotal: ${simResult.subtotal.toFixed(2)}</p>
                <p>Discount: ${simResult.discount_total.toFixed(2)}</p>
                <p>Grand Total: ${simResult.grand_total.toFixed(2)}</p>
                <p>Trace: {simResult.trace_id}</p>
              </div>
            )}
          </section>
        </main>
      )}

      {showFnCatalog && (
        <main className="workspace-grid two-col page-fn-catalog">
          <section className="card-panel">
            <h2>Commercial Item Management</h2>
            <form className="stack" onSubmit={createCatalogItem}>
              <input value={catalogDraft.item_code} onChange={(e) => setCatalogDraft({ ...catalogDraft, item_code: e.target.value })} placeholder="Item code" required />
              <input value={catalogDraft.name} onChange={(e) => setCatalogDraft({ ...catalogDraft, name: e.target.value })} placeholder="Item name" required />
              <select value={catalogDraft.item_type} onChange={(e) => setCatalogDraft({ ...catalogDraft, item_type: e.target.value })}>
                <option>LICENSED_SOFTWARE</option>
                <option>SUBSCRIPTION</option>
                <option>SERVICE</option>
                <option>HARDWARE</option>
                <option>TOKEN</option>
                <option>BUNDLE</option>
                <option>POC</option>
              </select>
              <button type="submit">Create Item</button>
            </form>
          </section>
          <section className="card-panel">
            <h2>Catalog</h2>
            <ul>
              {catalogItems.map((item) => (
                <li key={item.id} className="list-row">
                  <span>{item.item_code} - {item.name} ({item.item_type})</span>
                  <button className="secondary" onClick={() => setStatus('Activation toggled (next backend endpoint)')}>Activate/Deactivate</button>
                </li>
              ))}
            </ul>
          </section>
        </main>
      )}

      {showFnRules && (
        <main className="workspace-grid two-col page-fn-rules">
          <section className="card-panel">
            <h2>Human-readable Rule Builder</h2>
            <form className="stack" onSubmit={createRule}>
              <input value={ruleDraft.name} onChange={(e) => setRuleDraft({ ...ruleDraft, name: e.target.value })} placeholder="Rule name" required />
              <div className="inline-fields">
                <select value={ruleDraft.rule_type} onChange={(e) => setRuleDraft({ ...ruleDraft, rule_type: e.target.value })}>
                  <option>VALIDATION</option>
                  <option>PRICING</option>
                  <option>APPROVAL_TRIGGER</option>
                </select>
                <input type="number" value={ruleDraft.priority} onChange={(e) => setRuleDraft({ ...ruleDraft, priority: Number(e.target.value) })} />
              </div>
              <div className="inline-fields">
                <input value={ruleDraft.when_key} onChange={(e) => setRuleDraft({ ...ruleDraft, when_key: e.target.value })} placeholder="IF key" />
                <input value={ruleDraft.when_value} onChange={(e) => setRuleDraft({ ...ruleDraft, when_value: e.target.value })} placeholder="IF value" />
              </div>
              <div className="inline-fields">
                <input value={ruleDraft.then_key} onChange={(e) => setRuleDraft({ ...ruleDraft, then_key: e.target.value })} placeholder="THEN key" />
                <input value={ruleDraft.then_value} onChange={(e) => setRuleDraft({ ...ruleDraft, then_value: e.target.value })} placeholder="THEN value" />
              </div>
              <div className="inline-fields">
                <button type="submit">Save Rule</button>
                <button type="button" className="secondary" onClick={validateRule}>Validate Rule</button>
              </div>
            </form>
          </section>
          <section className="card-panel">
            <h2>Rules</h2>
            <ul>
              {rules.map((rule) => (
                <li key={rule.id}>{rule.name} | {rule.rule_type} | Priority {rule.priority} | {rule.status}</li>
              ))}
            </ul>
          </section>
        </main>
      )}

      {showFnRateCards && (
        <main className="workspace-grid two-col page-fn-ratecards">
          <section className="card-panel">
            <h2>Labor Rate Card</h2>
            <form className="stack" onSubmit={addRateCardRow}>
              <input value={rateCardDraft.role} onChange={(e) => setRateCardDraft({ ...rateCardDraft, role: e.target.value })} placeholder="Role" required />
              <div className="inline-fields">
                <input value={rateCardDraft.delivery} onChange={(e) => setRateCardDraft({ ...rateCardDraft, delivery: e.target.value })} placeholder="Delivery type" required />
                <input type="number" value={rateCardDraft.rate} onChange={(e) => setRateCardDraft({ ...rateCardDraft, rate: Number(e.target.value) })} required />
              </div>
              <div className="inline-fields">
                <input value={rateCardDraft.region} onChange={(e) => setRateCardDraft({ ...rateCardDraft, region: e.target.value })} placeholder="Region" required />
                <input type="date" value={rateCardDraft.effective} onChange={(e) => setRateCardDraft({ ...rateCardDraft, effective: e.target.value })} required />
              </div>
              <button type="submit">Add Rate Row</button>
            </form>
            <ul>
              {rateCardRows.map((row, idx) => (
                <li key={`${row.role}-${idx}`} className="list-row">
                  <span>{row.role} | {row.delivery} | {row.region} | ${row.rate}/hr | {row.effective}</span>
                </li>
              ))}
            </ul>
          </section>
          <section className="card-panel">
            <h2>Bulk Update</h2>
            <div className="stack">
              <input type="number" value={rateBulkPct} onChange={(e) => setRateBulkPct(Number(e.target.value))} />
              <button onClick={bulkUpdateRateCards}>Apply % uplift to all rates</button>
            </div>
          </section>
        </main>
      )}

      {showFnApprovalPolicies && (
        <main className="workspace-grid two-col page-fn-approval-policies">
          <section className="card-panel">
            <h2>Approval Policy Definition</h2>
            <form className="stack" onSubmit={createApprovalPolicy}>
              <input value={approvalPolicyDraft.name} onChange={(e) => setApprovalPolicyDraft({ ...approvalPolicyDraft, name: e.target.value })} required />
              <div className="inline-fields">
                <input type="number" value={approvalPolicyDraft.min_grand_total} onChange={(e) => setApprovalPolicyDraft({ ...approvalPolicyDraft, min_grand_total: Number(e.target.value) })} />
                <input type="number" value={approvalPolicyDraft.max_margin_pct} onChange={(e) => setApprovalPolicyDraft({ ...approvalPolicyDraft, max_margin_pct: Number(e.target.value) })} />
              </div>
              <input type="number" value={approvalPolicyDraft.levels} onChange={(e) => setApprovalPolicyDraft({ ...approvalPolicyDraft, levels: Number(e.target.value) })} />
              <button type="submit">Save Policy</button>
            </form>
          </section>
          <section className="card-panel">
            <h2>Policies</h2>
            <ul>
              {approvalPolicies.map((p) => (
                <li key={p.id}>{p.name} | Levels {p.route?.levels ?? 1} | Min {p.conditions?.min_grand_total ?? 0}</li>
              ))}
            </ul>
          </section>
        </main>
      )}

      {!isAdmin && endUserModule === 'DASHBOARD' && (
        <main className="workspace-grid one-col page-enduser-dashboard">
          <section className="card-panel">
            <h2>Dashboard & Visibility</h2>
            <div className="kpi-strip">
              <div><strong>Total Quotes</strong><span>{metrics?.total_quotes ?? 0}</span></div>
              <div><strong>Drafts</strong><span>{metrics?.draft_quotes ?? 0}</span></div>
              <div><strong>Pending</strong><span>{metrics?.pending_approvals ?? 0}</span></div>
              <div><strong>Pipeline</strong><span>${(metrics?.total_pipeline_value ?? 0).toFixed(2)}</span></div>
            </div>
            <div className="inline-fields">
              <input value={quoteSearch} onChange={(e) => setQuoteSearch(e.target.value)} placeholder="Search by quote no" />
              <select value={quoteStatusFilter} onChange={(e) => setQuoteStatusFilter(e.target.value)}>
                <option value="ALL">ALL</option>
                <option value="DRAFT">DRAFT</option>
                <option value="APPROVAL_PENDING">APPROVAL_PENDING</option>
                <option value="FINALIZED">FINALIZED</option>
                <option value="REJECTED">REJECTED</option>
              </select>
            </div>
            <ul>
              {filteredQuotes.map((quote) => (
                <li key={quote.id} className="list-row">
                  <button className="quote-chip" onClick={() => { setCurrentQuoteId(quote.id); void refreshQuoteDetails(quote.id) }}>
                    {quote.quote_no} | {quote.status} | ${quote.grand_total.toFixed(2)}
                  </button>
                  {quote.status === 'APPROVAL_PENDING' && (
                    <button
                      className="secondary"
                      onClick={() => {
                        setCurrentQuoteId(quote.id)
                        setEndUserModule('APPROVALS')
                        void refreshQuoteDetails(quote.id)
                      }}
                    >
                      Open Decision
                    </button>
                  )}
                </li>
              ))}
              {filteredQuotes.length === 0 && (
                <li className="empty-state">No quotes match this filter yet.</li>
              )}
            </ul>
          </section>
        </main>
      )}

      {!isAdmin && endUserModule === 'QUOTE_CREATE' && (
        <main className="quote-workspace guided-two-panel">
          <aside className="card-panel guided-summary-panel">
            <p className="eyebrow">Quote Summary</p>
            <h3>Live Context</h3>
            <div className="guided-meter">
              <div className="guided-meter-head">
                <span>Completion</span>
                <strong>{guidedSummaryProgress}%</strong>
              </div>
              <div className="guided-meter-track">
                <div className="guided-meter-fill" style={{ width: `${guidedSummaryProgress}%` }} />
              </div>
            </div>
            <div className="stack">
              <div className="preview">
                <p><strong>Customer Name</strong></p>
                <div className="guided-summary-line">
                  <p>{selectedGuidedCustomer?.name || ''}</p>
                  <span className={`guided-chip ${selectedGuidedCustomer?.name ? 'ready' : 'pending'}`}>
                    {selectedGuidedCustomer?.name ? 'Ready' : 'Pending'}
                  </span>
                </div>
              </div>
              <div className="preview">
                <p><strong>Opportunity Name</strong></p>
                <div className="guided-summary-line">
                  <p>{selectedGuidedOpportunity?.name || ''}</p>
                  <span className={`guided-chip ${selectedGuidedOpportunity?.name ? 'ready' : 'pending'}`}>
                    {selectedGuidedOpportunity?.name ? 'Ready' : 'Pending'}
                  </span>
                </div>
              </div>
              <div className="preview">
                <p><strong>Quote Details</strong></p>
                <p>1. Quote Term: {guidedQuoteTerm}</p>
                <p>2. Pricebook Used: {selectedGuidedPriceBook?.name || '-'}</p>
                <p className="guided-total">3. Quote Total ({guidedQuoteCurrency}): {guidedQuoteTotal.toFixed(2)}</p>
              </div>
            </div>
          </aside>

          <section className="guided-workhorse-panel">
          <section className="card-panel">
            <div className="section-head">
              <h2>Guided Quote Generation</h2>
              <span className="quote-meta">Step {guidedStep} of 7</span>
            </div>

            {guidedStep === 1 && (
              <div className="stack guided-step-pane" key="guided-step-1">
                <h3>Select Customer</h3>
                <input
                  placeholder="Search customers"
                  value={guidedCustomerSearch}
                  onChange={(e) => setGuidedCustomerSearch(e.target.value)}
                />
                <div className="split-half">
                  <div className="stack">
                    {guidedCustomersLoading && (
                      <>
                        <div className="skeleton-row" />
                        <div className="skeleton-row" />
                        <div className="skeleton-row" />
                      </>
                    )}
                    {guidedCustomers.map((customer) => (
                      <button
                        key={customer.id}
                        type="button"
                        className={guidedSelectedCustomerId === customer.id ? '' : 'secondary'}
                        onClick={() => setGuidedSelectedCustomerId(customer.id)}
                      >
                        {customer.name} ({customer.external_id})
                      </button>
                    ))}
                    {!guidedCustomersLoading && guidedCustomers.length === 0 && (
                      <div className="empty-state">No customers found. Create a new customer to continue.</div>
                    )}
                  </div>
                  <div className="stack">
                    <input
                      placeholder="Create new customer"
                      value={guidedCustomerName}
                      onChange={(e) => setGuidedCustomerName(e.target.value)}
                    />
                    <button type="button" onClick={() => void createGuidedCustomer()}>Create Customer</button>
                  </div>
                </div>
              </div>
            )}

            {guidedStep === 2 && (
              <div className="stack guided-step-pane" key="guided-step-2">
                <h3>Select Opportunity</h3>
                <input
                  placeholder="Search opportunities"
                  value={guidedOpportunitySearch}
                  onChange={(e) => setGuidedOpportunitySearch(e.target.value)}
                />
                <div className="split-half">
                  <div className="stack">
                    {guidedOpportunitiesLoading && (
                      <>
                        <div className="skeleton-row" />
                        <div className="skeleton-row" />
                      </>
                    )}
                    {guidedOpportunities.map((opp) => (
                      <button
                        key={opp.id}
                        type="button"
                        className={guidedSelectedOpportunityId === opp.id ? '' : 'secondary'}
                        onClick={() => setGuidedSelectedOpportunityId(opp.id)}
                      >
                        {opp.name} ({opp.stage})
                      </button>
                    ))}
                    {!guidedOpportunitiesLoading && guidedOpportunities.length === 0 && (
                      <div className="empty-state">No opportunities found. Create one and continue.</div>
                    )}
                  </div>
                  <div className="stack">
                    <input
                      placeholder="Create new opportunity"
                      value={guidedOpportunityName}
                      onChange={(e) => setGuidedOpportunityName(e.target.value)}
                    />
                    <button type="button" onClick={() => void createGuidedOpportunity()}>Create Opportunity</button>
                  </div>
                </div>
              </div>
            )}

            {guidedStep === 3 && (
              <div className="stack guided-step-pane" key="guided-step-3">
                <h3>Clone Existing Quote or Start New</h3>
                <button type="button" className={guidedCloneQuoteId ? 'secondary' : ''} onClick={() => setGuidedCloneQuoteId('')}>
                  Start New Quote
                </button>
                {guidedCustomerQuotes.map((quote) => (
                  <button
                    key={quote.id}
                    type="button"
                    className={guidedCloneQuoteId === quote.id ? '' : 'secondary'}
                    onClick={() => setGuidedCloneQuoteId(quote.id)}
                  >
                    Clone {quote.quote_no} ({quote.status}) ${Number(quote.grand_total || 0).toFixed(2)}
                  </button>
                ))}
                {guidedQuotesLoading && (
                  <>
                    <div className="skeleton-row" />
                    <div className="skeleton-row" />
                  </>
                )}
                {!guidedQuotesLoading && guidedCustomerQuotes.length === 0 && (
                  <div className="empty-state">No existing quotes for this customer. Proceed with a new quote.</div>
                )}
              </div>
            )}

            {guidedStep === 4 && (
              <div className="stack guided-step-pane" key="guided-step-4">
                <h3>General Questions</h3>
                <div className="inline-fields">
                  <select value={guidedGeneral.duration_type} onChange={(e) => setGuidedGeneral((prev) => ({ ...prev, duration_type: e.target.value }))}>
                    <option value="ONETIME">Onetime</option>
                    <option value="YEARS">Years</option>
                    <option value="MONTHS">Months</option>
                  </select>
                  <input
                    type="number"
                    min={1}
                    value={guidedGeneral.duration_value}
                    onChange={(e) => setGuidedGeneral((prev) => ({ ...prev, duration_value: Number(e.target.value) }))}
                  />
                </div>
                <div className="inline-fields">
                  <input
                    type="date"
                    value={guidedGeneral.valid_until}
                    onChange={(e) => setGuidedGeneral((prev) => ({ ...prev, valid_until: e.target.value }))}
                  />
                  <select value={guidedGeneral.price_book_id} onChange={(e) => setGuidedGeneral((prev) => ({ ...prev, price_book_id: e.target.value }))}>
                    <option value="">Select Price Book</option>
                    {priceBooks.map((book) => <option key={book.id} value={book.id}>{book.name} ({book.status})</option>)}
                  </select>
                </div>
                <div className="inline-fields">
                  <select value={guidedGeneral.currency} onChange={(e) => setGuidedGeneral((prev) => ({ ...prev, currency: e.target.value }))}>
                    {['USD', 'EUR', 'GBP', 'INR'].map((cur) => <option key={cur}>{cur}</option>)}
                  </select>
                  <input value={guidedGeneral.region} onChange={(e) => setGuidedGeneral((prev) => ({ ...prev, region: e.target.value }))} placeholder="Region" />
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={guidedGeneral.overall_discount_pct}
                    onChange={(e) => setGuidedGeneral((prev) => ({ ...prev, overall_discount_pct: Number(e.target.value) }))}
                    placeholder="Overall Discount %"
                  />
                </div>
              </div>
            )}

            {guidedStep === 5 && (
              <div className="stack guided-step-pane" key="guided-step-5">
                <h3>Products, Quantities, Discounts</h3>
                {guidedLines.map((line, idx) => (
                  <div key={`guided-line-${idx}`} className="inline-fields">
                    <select value={line.commercial_item_id} onChange={(e) => updateGuidedLine(idx, { commercial_item_id: e.target.value })}>
                      <option value="">Select Product</option>
                      {catalogItems.map((item) => <option key={item.id} value={item.id}>{item.item_code} - {item.name}</option>)}
                    </select>
                    <input
                      type="number"
                      min={1}
                      value={line.quantity_per_period}
                      onChange={(e) => updateGuidedLine(idx, { quantity_per_period: Number(e.target.value) })}
                      placeholder="Qty / period"
                    />
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={line.line_discount_pct}
                      onChange={(e) => updateGuidedLine(idx, { line_discount_pct: Number(e.target.value) })}
                      placeholder="Line discount %"
                    />
                    <button type="button" className="secondary" onClick={() => removeGuidedLine(idx)} disabled={guidedLines.length <= 1}>Remove</button>
                  </div>
                ))}
                <button type="button" className="secondary" onClick={addGuidedLine}>Add Product</button>
              </div>
            )}

            {guidedStep === 6 && (
              <div className="stack guided-step-pane" key="guided-step-6">
                <h3>Generate Quote</h3>
                <p className="quote-meta">Review your selections and generate quote with full calculation.</p>
                <button type="button" onClick={() => void generateGuidedQuote()} disabled={guidedGenerating}>
                  {guidedGenerating ? 'Generating Quote...' : 'Generate Quote'}
                </button>
              </div>
            )}

            {guidedStep === 7 && (
              <div className="stack guided-step-pane" key="guided-step-7">
                <h3>Review and Regenerate</h3>
                <p className="quote-meta">Generated quote can be edited below and regenerated anytime.</p>
                {guidedResult && (
                  <div className="preview">
                    <p>Quote: {guidedResult.quote?.quote_no}</p>
                    <p>Subtotal: ${Number(guidedResult.computation?.subtotal || 0).toFixed(2)}</p>
                    <p>Grand Total: ${Number(guidedResult.preview?.grand_total || 0).toFixed(2)}</p>
                    <p>Margin: {Number(guidedResult.preview?.margin_pct || 0).toFixed(2)}%</p>
                  </div>
                )}
                <button type="button" className="secondary" onClick={() => setGuidedStep(5)}>Edit Products and Regenerate</button>
                <button type="button" onClick={() => void generateGuidedQuote()} disabled={guidedGenerating}>
                  {guidedGenerating ? 'Regenerating...' : 'Regenerate Quote'}
                </button>
              </div>
            )}

            <div className="inline-fields">
              <button type="button" className="secondary" disabled={guidedStep <= 1} onClick={() => setGuidedStep((prev) => Math.max(1, prev - 1))}>Back</button>
              <button
                type="button"
                disabled={
                  (guidedStep === 1 && !guidedSelectedCustomerId)
                  || (guidedStep === 2 && !guidedSelectedOpportunityId && guidedOpportunities.length > 0)
                  || guidedStep >= 6
                }
                onClick={() => {
                  if (guidedStep === 2 && guidedSelectedCustomerId) void loadCustomerQuoteHistory(guidedSelectedCustomerId)
                  setGuidedStep((prev) => Math.min(7, prev + 1))
                }}
              >
                Next
              </button>
            </div>
          </section>

          <section className="quote-header-sticky card-panel">
            <div className="quote-header-top">
              <div>
                <p className="eyebrow">Deal Context</p>
                <h2>{currentQuote ? currentQuote.quote_no : 'New Draft Quote'}</h2>
              </div>
              <span className={`status-badge ${currentQuote?.status || 'DRAFT'}`}>{currentQuote?.status || 'DRAFT'}</span>
            </div>
            <div className="quote-header-grid">
              <input
                placeholder="Customer / Account"
                value={quoteDraft.customer_external_id}
                onChange={(e) => {
                  setQuoteDraft({ ...quoteDraft, customer_external_id: e.target.value })
                  setSaveState('DIRTY')
                }}
              />
              <select value={quoteDraft.price_book_id} onChange={(e) => void selectPriceBookForQuote(e.target.value)} required>
                <option value="">Select Price Book</option>
                {priceBooks.map((book) => <option key={book.id} value={book.id}>{book.name} ({book.status})</option>)}
              </select>
              <select value={quoteDraft.currency} onChange={(e) => selectCurrencyForQuote(e.target.value)}>
                {['USD', 'EUR', 'GBP', 'INR'].map((cur) => <option key={cur}>{cur}</option>)}
              </select>
              <input value={quoteDraft.region} onChange={(e) => setQuoteDraft({ ...quoteDraft, region: e.target.value })} />
              <div className="quote-meta">Created By: {email || 'ui-user'} | {new Date().toLocaleDateString()}</div>
              <div className="quote-meta">Save State: {saveState}{lastSavedAt ? ` | ${lastSavedAt}` : ''}</div>
            </div>
          </section>

          <section className="quote-3pane">
            <aside className="card-panel quote-left">
              <h3>Catalog</h3>
              <input
                placeholder="Search catalog..."
                value={catalogSearch}
                onChange={(e) => setCatalogSearch(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && filteredCatalogItems[0]) {
                    e.preventDefault()
                    void addLineByPayload({ commercial_item_id: filteredCatalogItems[0].id, quantity: 1, discount_pct: 0 })
                  }
                }}
              />
              <select value={catalogFilter} onChange={(e) => setCatalogFilter(e.target.value)}>
                {catalogTypes.map((type) => <option key={type}>{type}</option>)}
              </select>
              <div className="catalog-scroll">
                {filteredCatalogItems.map((item) => (
                  <div
                    key={item.id}
                    className={`catalog-item ${selectedCatalogItemId === item.id ? 'active' : ''}`}
                    role="button"
                    tabIndex={0}
                    draggable
                    onDragStart={(e) => e.dataTransfer.setData('text/plain', item.id)}
                    onClick={() => setSelectedCatalogItemId(item.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') setSelectedCatalogItemId(item.id)
                    }}
                  >
                    <div className="catalog-row-head">
                      <strong>{item.name}</strong>
                      <span className="type-chip">{item.item_type}</span>
                    </div>
                    <small>{item.item_code}</small>
                    <div className="catalog-row-actions">
                      <button type="button" onClick={(e) => { e.stopPropagation(); toggleFavorite(item.id) }}>{favoriteItemIds.includes(item.id) ? 'Unfavorite' : 'Favorite'}</button>
                      <button type="button" className="secondary" onClick={(e) => { e.stopPropagation(); void addLineByPayload({ commercial_item_id: item.id, quantity: 1, discount_pct: 0 }) }}>Add</button>
                    </div>
                  </div>
                ))}
              </div>
              {selectedCatalogItem && (
                <div className="preview">
                  <p><strong>Quick View:</strong> {selectedCatalogItem.name}</p>
                  <p>Type: {selectedCatalogItem.item_type}</p>
                  <p>Compatibility: {selectedCatalogItem.item_type === 'BUNDLE' ? 'Bundle container, supports child options' : 'No blocking dependency'}</p>
                </div>
              )}
              <p className="quote-meta">Favorites: {favoriteItemIds.length} | Recently Used: {recentItemIds.length}</p>
            </aside>

            <section
              className="card-panel quote-center"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                const itemId = e.dataTransfer.getData('text/plain')
                if (itemId) void addLineByPayload({ commercial_item_id: itemId, quantity: 1, discount_pct: 0 })
              }}
            >
              <h3>Quote Builder</h3>
              <form className="line-inline-add" onSubmit={addLine}>
                <select value={lineDraft.commercial_item_id} onChange={(e) => setLineDraft({ ...lineDraft, commercial_item_id: e.target.value })} required>
                  <option value="">Select item</option>
                  {catalogItems.map((item) => <option key={item.id} value={item.id}>{item.item_code} - {item.name}</option>)}
                </select>
                <input type="number" min={1} value={lineDraft.quantity} onChange={(e) => setLineDraft({ ...lineDraft, quantity: Number(e.target.value) })} />
                <input type="number" min={0} max={100} value={lineDraft.discount_pct} onChange={(e) => setLineDraft({ ...lineDraft, discount_pct: Number(e.target.value) })} />
                <button type="submit">Add</button>
              </form>

              <div className="line-table quote-line-grid">
                <div className="line-head">
                  <span>Item</span><span>Qty</span><span>Unit</span><span>Adjust</span><span>Net</span><span>State</span>
                </div>
                {quoteLines.slice(0, 100).map((line) => {
                  const item = catalogItems.find((c) => c.id === line.commercial_item_id)
                  const edit = lineEdits[line.id] || { quantity: Number(line.quantity), discount_pct: Number(line.discount_pct) }
                  const expanded = expandedLineIds.includes(line.id)
                  return (
                    <div key={line.id} className="line-block">
                      <div
                        className="line-row line-row-button"
                        role="button"
                        tabIndex={0}
                        onClick={() => toggleLineExpanded(line.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') toggleLineExpanded(line.id)
                        }}
                      >
                        <span>{item?.name || line.commercial_item_id}</span>
                        <span>{line.quantity}</span>
                        <span>
                          <button type="button" className="link-button" onClick={(e) => { e.stopPropagation(); openPricingDrawer(line.id) }}>
                            ${(line.unit_price ?? 0).toFixed(2)}
                          </button>
                        </span>
                        <span>{line.discount_pct}%</span>
                        <span>
                          <button type="button" className="link-button" onClick={(e) => { e.stopPropagation(); openPricingDrawer(line.id) }}>
                            ${(line.net_price ?? 0).toFixed(2)}
                          </button>
                        </span>
                        <span>
                          <button type="button" className="link-button" onClick={(e) => { e.stopPropagation(); openPricingDrawer(line.id) }}>
                            {line.discount_pct > 35 ? 'Warning' : 'Valid'}
                          </button>
                        </span>
                      </div>
                      {expanded && (
                        <div className="line-expand">
                          <div className="inline-fields">
                            <input
                              type="number"
                              min={1}
                              value={edit.quantity}
                              onChange={(e) => setLineEdits((prev) => ({ ...prev, [line.id]: { ...edit, quantity: Number(e.target.value) } }))}
                            />
                            <input
                              type="number"
                              min={0}
                              max={100}
                              value={edit.discount_pct}
                              onChange={(e) => setLineEdits((prev) => ({ ...prev, [line.id]: { ...edit, discount_pct: Number(e.target.value) } }))}
                            />
                          </div>
                          <div className="inline-fields">
                            <button type="button" onClick={() => void updateLineItem(line.id, { quantity: edit.quantity, discount_pct: edit.discount_pct })}>Apply Update</button>
                            <button type="button" className="secondary" onClick={() => void removeLineItem(line.id)}>Remove Line</button>
                          </div>
                          <div className="preview">
                            <p>Pricing explanation: base ${(line.unit_price ?? 0).toFixed(2)}, discount {line.discount_pct}%, net ${(line.net_price ?? 0).toFixed(2)}</p>
                            <p>Bundle logic: {item?.item_type === 'BUNDLE' ? 'Parent container. Expand child items in future iteration.' : 'Standalone line item.'}</p>
                            <p>Dependency checks: {line.discount_pct > 30 ? 'Soft warning, review policy threshold.' : 'No rule conflicts detected.'}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
              {quoteLines.length > 100 && <p className="quote-meta">Showing first 100 rows for performance.</p>}
            </section>

            <aside className="card-panel quote-right">
              <h3>Financial Summary</h3>
              <div className="kpi-strip compact">
                <div><strong>Subtotal</strong><span>${(preview?.subtotal ?? 0).toFixed(2)}</span></div>
                <div><strong>Discounts</strong><span>${(preview?.discount_total ?? 0).toFixed(2)}</span></div>
                <div><strong>Taxes</strong><span>$0.00</span></div>
                <div><strong>Grand Total</strong><span>${(preview?.grand_total ?? 0).toFixed(2)}</span></div>
              </div>
              <div className="preview">
                <p>
                  Margin:{' '}
                  <button
                    type="button"
                    className="link-button"
                    onClick={() => {
                      const firstLine = quoteLines[0]
                      if (firstLine) openPricingDrawer(firstLine.id)
                    }}
                  >
                    {(preview?.margin_pct ?? 0).toFixed(2)}%
                  </button>
                </p>
                <p>Indicator: {(preview?.margin_pct ?? 0) < 15 ? 'Approval Required' : (preview?.margin_pct ?? 0) < 22 ? 'Warning' : 'Safe'}</p>
              </div>
              <div className="preview">
                <p><strong>Pricing Insights</strong></p>
                <p>Rules Triggered: {(preview?.line_breakdown || []).length}</p>
                <p>Anomalies: {warnings.length}</p>
                <p>AI Suggestion: {aiSuggestions?.suggestion || 'No suggestion yet'}</p>
                <p>Approval Impact: {approvalImpact}</p>
              </div>
              <div className="preview">
                <p><strong>Error vs Warning</strong></p>
                {blockingErrors.length > 0 && <p className="panel-alert error">{blockingErrors.join(' | ')}</p>}
                {warnings.length > 0 && <p className="panel-alert warn">{warnings.join(' | ')}</p>}
              </div>
            </aside>
          </section>

          <section className="quote-footer-sticky card-panel">
            <div className="footer-actions-row">
              <button onClick={() => void saveDraftQuote()}>Save Draft</button>
              <button onClick={submitForApproval} disabled={!currentQuoteId || currentQuote?.status === 'APPROVAL_PENDING'}>Submit for Approval</button>
              <button className="secondary" onClick={queuePdf} disabled={!currentQuoteId}>Generate Proposal</button>
              <button className="secondary" onClick={() => void archiveCurrentQuote()} disabled={!currentQuoteId}>Cancel / Delete</button>
              <button className="secondary" onClick={() => void duplicateCurrentQuote()} disabled={!currentQuoteId}>Duplicate Quote</button>
            </div>
          </section>

          {pricingDrawerOpen && (
            <aside className="pricing-drawer">
              <div className="pricing-drawer-head">
                <h3>Pricing Explanation</h3>
                <button className="secondary" type="button" onClick={() => setPricingDrawerOpen(false)}>Close</button>
              </div>

              {!selectedExplanation && <p>Select a quote line to inspect pricing explanation.</p>}

              {selectedExplanation && (
                <div className="stack">
                  <section className="preview">
                    <h4>Item Summary</h4>
                    <p>{selectedExplanation.item_summary?.item_name}</p>
                    <p>Type: {selectedExplanation.item_summary?.item_type}</p>
                    <p>Pricing Model: {selectedExplanation.item_summary?.pricing_model}</p>
                    <p>Price Book: {selectedExplanation.item_summary?.price_book_source}</p>
                    <p>Currency: {selectedExplanation.item_summary?.currency}</p>
                    <p>{selectedExplanation.item_summary?.quantity_impact_notice}</p>
                  </section>

                  <section className="preview">
                    <h4>Calculation Breakdown</h4>
                    {(selectedExplanation.calculation_breakdown || []).map((step: any, idx: number) => (
                      <p key={idx}>{step.label}: {step.operator} ${Number(step.amount || 0).toFixed(2)}</p>
                    ))}
                  </section>

                  <section className="preview">
                    <h4>Rules & Adjustments</h4>
                    {(selectedExplanation.rules_applied || []).map((rule: any, idx: number) => (
                      <details key={idx}>
                        <summary>{rule.name} ({rule.impact_amount >= 0 ? '+' : ''}{Number(rule.impact_amount || 0).toFixed(2)})</summary>
                        <p>Trigger: {rule.trigger_condition}</p>
                        <p>Impact: ${Number(rule.impact_amount || 0).toFixed(2)}</p>
                        <p>Source: {rule.source}</p>
                        <p>{rule.statement}</p>
                      </details>
                    ))}
                  </section>

                  <section className="preview">
                    <h4>Discounts & Overrides</h4>
                    {(selectedExplanation.discounts_overrides || []).map((d: any, idx: number) => (
                      <p key={idx}>
                        {d.type}: {Number(d.percent || 0).toFixed(2)}% (${Number(d.amount || 0).toFixed(2)}) | by {d.applied_by}
                      </p>
                    ))}
                  </section>

                  <section className="preview">
                    <h4>Warnings / Approvals</h4>
                    {(selectedExplanation.warnings || []).map((w: any, idx: number) => (
                      <p key={idx}>⚠ {w.message}</p>
                    ))}
                    {(preview?.approval_signals || []).map((sig: any, idx: number) => (
                      <p key={`ap-${idx}`}>{sig.severity === 'WARNING' ? '⚠' : 'ℹ'} {sig.message}</p>
                    ))}
                  </section>

                  <section className="preview">
                    <h4>Price Delta</h4>
                    <p>
                      ${Number(selectedExplanation.delta?.previous_net_price || 0).toFixed(2)} → ${Number(selectedExplanation.delta?.current_net_price || 0).toFixed(2)}
                    </p>
                    <p>Reason: {selectedExplanation.delta?.reason}</p>
                  </section>

                  <section className="preview">
                    <h4>Simulation Mode</h4>
                    <div className="inline-fields">
                      <input type="number" min={1} value={simQuantity} onChange={(e) => setSimQuantity(Number(e.target.value))} />
                      <input type="number" min={0} max={100} value={simDiscount} onChange={(e) => setSimDiscount(Number(e.target.value))} />
                    </div>
                    <p>Simulated Net: ${simulateNetPrice(selectedExplanation, simQuantity, simDiscount).toFixed(2)}</p>
                    <p className="quote-meta">Preview only. Quote is unchanged until line update is applied.</p>
                  </section>

                  <section className="preview">
                    <h4>Rule Impact Heatmap</h4>
                    {(() => {
                      const points = preview?.rule_impact_heatmap || []
                      const maxImpact = Math.max(1, ...points.map((p: any) => Number(p.impact || 0)))
                      return points.map((point: any) => (
                        <div key={point.driver} className="heat-row">
                          <span>{point.driver}</span>
                          <div className="heat-bar-wrap">
                            <div className="heat-bar" style={{ width: `${(Number(point.impact || 0) / maxImpact) * 100}%` }} />
                          </div>
                        </div>
                      ))
                    })()}
                  </section>

                  <section className="preview">
                    <h4>Audit Metadata</h4>
                    <p>Price Book Version: {selectedExplanation.audit_metadata?.price_book_version}</p>
                    <p>Calculation Timestamp: {selectedExplanation.audit_metadata?.calculation_timestamp}</p>
                    <p>Engine Version: {selectedExplanation.audit_metadata?.pricing_engine_version}</p>
                    <p>Last Modified By: {selectedExplanation.audit_metadata?.last_modified_by}</p>
                    <p>Triggers: {(selectedExplanation.audit_metadata?.recalculation_triggers || []).join(', ')}</p>
                  </section>
                </div>
              )}
            </aside>
          )}
          </section>
        </main>
      )}

      {!isAdmin && endUserModule === 'REVISIONS' && (
        <main className="workspace-grid two-col page-enduser-revisions">
          <section className="card-panel">
            <h2>Quote Revisioning</h2>
            <div className="stack">
              <button onClick={() => createRevision('Updated line item mix')}>Create Revision</button>
              <p>{diffSummary()}</p>
            </div>
            <ul>
              {revisions.map((rev) => (
                <li key={rev.id}>Rev {rev.revision_no} | {rev.change_reason}</li>
              ))}
            </ul>
          </section>
          <section className="card-panel">
            <h2>Line-by-line Diff View</h2>
            {buildRevisionDiff().length > 0 ? (
              <div className="diff-table">
                <div className="diff-head">
                  <span>Line Key</span>
                  <span>Change</span>
                  <span>Before</span>
                  <span>After</span>
                </div>
                {buildRevisionDiff().map((row) => (
                  <div className="diff-row" key={row.key}>
                    <span>{row.key}</span>
                    <span>{row.change}</span>
                    <span>{row.before}</span>
                    <span>{row.after}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p>Create at least two revisions to compare line changes.</p>
            )}
          </section>
        </main>
      )}

      {!isAdmin && endUserModule === 'APPROVALS' && (
        <main className="decision-workspace page-enduser-approvals">
          <section className="card-panel decision-header">
            <div>
              <p className="eyebrow">Approval Decision Workspace</p>
              <h2>{currentQuote?.quote_no || 'Select a Quote'}</h2>
              <p>
                Customer: {quoteDraft.customer_external_id || 'N/A'} | Submitted by: {email || 'ui-user'}
              </p>
            </div>
            <div className="stack">
              <span className={`status-badge ${approvalState?.status || 'PENDING'}`}>{approvalState?.status || 'PENDING'}</span>
              <p>Stage: {currentApprovalStep ? `${currentApprovalStep.approver_role} (Level ${currentApprovalStep.seq_no})` : 'Not started'}</p>
              <p>Pending for: {approvalAgeHours} hours</p>
              <button type="button" onClick={submitForApproval} disabled={!currentQuoteId || !!approvalState?.id}>
                Submit for Approval
              </button>
            </div>
          </section>

          <section className="decision-grid">
            <section className="card-panel decision-left">
              <h3>Deal Snapshot</h3>
              <div className="kpi-strip compact">
                <div><strong>Total Deal Value</strong><span>${(preview?.grand_total ?? 0).toFixed(2)}</span></div>
                <div><strong>Discount %</strong><span>{preview?.subtotal ? (((preview?.discount_total ?? 0) / preview.subtotal) * 100).toFixed(2) : '0.00'}%</span></div>
                <div><strong>Margin %</strong><span>{(preview?.margin_pct ?? 0).toFixed(2)}%</span></div>
                <div><strong>Term</strong><span>12 mo</span></div>
              </div>

              <h4>Key Deal Composition</h4>
              <ul>
                {quoteLines.slice(0, 5).map((line) => {
                  const item = catalogItems.find((c) => c.id === line.commercial_item_id)
                  return (
                    <li key={line.id} className="list-row">
                      <span>{item?.name || line.commercial_item_id}</span>
                      <span>${Number(line.net_price || 0).toFixed(2)}</span>
                    </li>
                  )
                })}
              </ul>

              <h4>What Changed?</h4>
              <div className="preview">
                {approvalDelta ? (
                  <>
                    <p>Total: ${approvalDelta.grandTotalFrom.toFixed(2)} → ${approvalDelta.grandTotalTo.toFixed(2)}</p>
                    <p>Margin: {approvalDelta.marginFrom.toFixed(2)}% → {approvalDelta.marginTo.toFixed(2)}%</p>
                  </>
                ) : (
                  <p>No prior revision deltas available.</p>
                )}
                <p>Line changes: {buildRevisionDiff().length}</p>
              </div>

              <h4>Policy Signals</h4>
              <ul>
                {decisionRisks.map((risk, idx) => (
                  <li key={idx} className="list-row"><span>⚠ {risk}</span></li>
                ))}
              </ul>
            </section>

            <section className="card-panel decision-right">
              <div className="decision-right-head">
                <h3>Decision Panel</h3>
                <label className="matrix-toggle">
                  <span>Compact Mode</span>
                  <input type="checkbox" checked={decisionCompactMode} onChange={() => setDecisionCompactMode((v) => !v)} />
                </label>
              </div>

              <div className="preview">
                <p>Risk Score: {aiRisk?.risk_score ?? '-'}</p>
                {!decisionCompactMode && <p>AI Suggestion: {aiSuggestions?.suggestion ?? 'No suggestion'}</p>}
              </div>

              {!decisionCompactMode && (
                <>
                  <h4>Submitter Justification</h4>
                  <p className="preview">{revisions[revisions.length - 1]?.change_reason || 'No submitter note provided.'}</p>

                  <h4>Approval Chain</h4>
                  <ul>
                    {approvalTimeline.map((step) => (
                      <li key={step.step_id} className="list-row">
                        <span>{step.status === 'APPROVED' ? '✔' : step.status === 'PENDING' ? '⏳' : '•'} {step.approver_role} (L{step.seq_no})</span>
                        <span>{step.status}</span>
                      </li>
                    ))}
                  </ul>

                  <h4>Approval Impact Simulator</h4>
                  <div className="inline-fields">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={decisionAdjustDiscount}
                      onChange={(e) => setDecisionAdjustDiscount(Number(e.target.value))}
                    />
                    <button type="button" className="secondary" onClick={() => void applyApprovalDiscountAdjustment()}>
                      Apply Discount Adjustment
                    </button>
                  </div>
                  {(() => {
                    const estimate = estimateMarginAfterAdjustment()
                    return estimate ? (
                      <div className="preview">
                        <p>Estimated Total: ${estimate.proposedTotal.toFixed(2)}</p>
                        <p>Estimated Margin: {estimate.proposedMargin.toFixed(2)}%</p>
                      </div>
                    ) : null
                  })()}
                </>
              )}

              <h4>Decision Comment</h4>
              <textarea
                rows={4}
                value={decisionComment}
                onChange={(e) => setDecisionComment(e.target.value)}
                placeholder="Add rationale, rejection reason, or requested changes"
              />
            </section>
          </section>

          <section className="card-panel decision-footer">
            <div className="footer-actions-row">
              <button onClick={() => void decisionAction('APPROVE')} disabled={approvalState?.status !== 'PENDING'}>Approve</button>
              <button className="secondary" onClick={() => void decisionAction('REJECT')} disabled={approvalState?.status !== 'PENDING'}>Reject</button>
              <button className="secondary" onClick={() => void decisionAction('REQUEST_CHANGES')} disabled={approvalState?.status !== 'PENDING'}>
                Request Changes
              </button>
              <button className="secondary" onClick={() => void escalateApprovalReminder()} disabled={!approvalState?.id}>
                Escalate
              </button>
            </div>
          </section>
        </main>
      )}

      {!isAdmin && endUserModule === 'OUTPUT' && (
        <main className="workspace-grid two-col page-enduser-output">
          <section className="card-panel">
            <h2>Quote Output / Sharing</h2>
            <div className="stack">
              <button onClick={queuePdf} disabled={!currentQuoteId}>Generate PDF / Proposal</button>
              <button className="secondary" onClick={() => setStatus('Share link generated (UI baseline)')}>Create Shareable Link</button>
              <button className="secondary" onClick={() => setStatus('Version stamped export prepared')}>Export with Version Stamp</button>
            </div>
            {lastPdfJob && (
              <div className="preview">
                <p>Job: {lastPdfJob.task_id}</p>
                <p>Status: {lastPdfJob.status}</p>
              </div>
            )}
          </section>
          <section className="card-panel">
            <h2>Branding & Proposal Preview</h2>
            <div className="preview">
              <p>Brand color from tenant: {orgSettings.primary_color}</p>
              <p>Quote number: {quotes.find((q) => q.id === currentQuoteId)?.quote_no || '-'}</p>
              <p>Prepared for customer: {quoteDraft.customer_external_id || '-'}</p>
            </div>
          </section>
        </main>
      )}

      {status && <footer className="status workspace-status">{status}</footer>}
    </div>
  )
}

export default App
