import { type RouteConfig, index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("callback", "routes/callback.tsx"),
  route(".well-known/appspecific/com.chrome.devtools.json", "routes/devtools.ts"),
  route("*", "routes/not-found.tsx"),
] satisfies RouteConfig;
