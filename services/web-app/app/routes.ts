import { type RouteConfig, index, route, layout } from "@react-router/dev/routes";

export default [
  layout("components/layout/DashboardLayout.tsx", [
    route("buyer/dashboard", "routes/dashboard.tsx"),
    route("buyer/wizard", "routes/wizard.tsx"),
    route("buyer/credits", "routes/buyer-credits.tsx"),
    route("marketplace", "routes/marketplace.tsx"),
    route("seller/listings", "routes/seller-listings.tsx"),
  ]),
  index("routes/home.tsx"),
  route("callback", "routes/callback.tsx"),
  route(".well-known/appspecific/com.chrome.devtools.json", "routes/devtools.ts"),
  route("*", "routes/not-found.tsx"),
] satisfies RouteConfig;
