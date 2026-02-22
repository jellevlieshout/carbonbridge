import { type RouteConfig, index, route, layout } from "@react-router/dev/routes";

export default [
  layout("components/layout/DashboardLayout.tsx", [
    route("buyer/dashboard", "routes/dashboard.tsx"),
    route("buyer/wizard", "routes/wizard.tsx"),
    route("buyer/credits", "routes/buyer-credits.tsx"),
    route("marketplace", "routes/marketplace.tsx"),
    route("buyer/agent", "routes/buyer-agent.tsx"),
    route("seller/agent", "routes/seller-agent.tsx"),
    route("seller/listings", "routes/seller-listings.tsx"),
    route("platform/transactions", "routes/platform-transactions.tsx"),
    route("platform/accounting", "routes/platform-accounting.tsx"),
    route("platform/glossary", "routes/platform-glossary.tsx"),
    route("trust/registry", "routes/trust-registry.tsx"),
    route("trust/standards", "routes/trust-standards.tsx"),
    route("trust/support", "routes/trust-support.tsx"),
  ]),
  index("routes/home.tsx"),
  route("onboarding", "routes/onboarding.tsx"),
  route("callback", "routes/callback.tsx"),
  route(".well-known/appspecific/com.chrome.devtools.json", "routes/devtools.ts"),
  route("*", "routes/not-found.tsx"),
] satisfies RouteConfig;
