Week 1
Day	Goal	2-3 Hour Vibe Coding Window Task
1	Tooling & Subs	Install Antigravity. Sub to Google AI Pro ($20) & OpenAI Plus ($20). Connect GitHub.
2	Project Init	Prompt Antigravity: "Scaffold a mono-repo with /frontend (Vite+React) and /backend (FastAPI). Setup Dockerfiles."
3	Supabase DB	Create Supabase project. Define tenants and profiles tables with RLS. Link to Backend.
4	Auth Flow	Implement Supabase Auth in React. Create a 'Landing' vs 'Dashboard' protected route.
5	Tenant Context	Build FastAPI middleware to extract X-Tenant-ID from JWT and apply to all DB queries.
6	Cloud Deploy	Connect GitHub to Railway. Deploy Backend. Deploy Frontend to Vercel/Railway. Verify "Live" link.
7	Buffer/Refactor	Ask Antigravity Agent: "Audit my RLS policies for security flaws and optimize Docker build speed."

Week 2
Day,Goal,2-3 Hour Vibe Coding Window Task
1,Deal Schema,"SQL Day: Create deals, deal_items, and price_books tables. Run migrations via Antigravity terminal."
2,Backend API,Create FastAPI endpoints for POST /deals and GET /deals (must be tenant-aware).
3,Deal Wizard UI,Build a multi-step form in React: 1. Customer Info -> 2. Product Selection -> 3. Pricing/Discounts.
4,Line Item Logic,"Frontend math: Automatically calculate Total, Margin, and Tax as the user adds products."
5,Agentic Validation,"Build a ""Validation"" endpoint that checks for missing data before a deal can be ""Submitted."""
6,Dashboard View,"Create a searchable table of all ""My Deals"" with status badges (Draft, Pending, Approved)."
7,Review & Sync,"Final push to GitHub. Ask Agent: ""Check for any UI/UX inconsistencies and fix Tailwind responsive issues."""