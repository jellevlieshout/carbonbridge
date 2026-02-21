import { type RouteConfig, index, route, layout } from "@react-router/dev/routes";

export default [
  layout("components/layout/DashboardLayout.tsx", [
    route("buyer/dashboard", "routes/dashboard.tsx"),
  ]),
  index("routes/home.tsx"),
  route("callback", "routes/callback.tsx"),
  route(".well-known/appspecific/com.chrome.devtools.json", "routes/devtools.ts"),
  route("*", "routes/not-found.tsx"),
] satisfies RouteConfig;
