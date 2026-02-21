import {
  isRouteErrorResponse,
  Links,
  Meta,
  Outlet,
  Scripts,
  ScrollRestoration,
} from "react-router";

import type { Route } from "./+types/root";
import "./app.css";

export const meta: Route.MetaFunction = () => [
  { title: "CarbonBridge" },
  { name: "description", content: "Carbon Bridge - Connecting Carbon Markets" },
];

export const links: Route.LinksFunction = () => [
  {
    rel: "icon",
    type: "image/png",
    href: "/favicon-32x32.png",
    media: "(prefers-color-scheme: light)"
  },
  {
    rel: "icon",
    type: "image/png",
    href: "/favicon-32x32.png",
    media: "(prefers-color-scheme: dark)"
  },
  { rel: "preconnect", href: "https://fonts.googleapis.com" },
  {
    rel: "preconnect",
    href: "https://fonts.gstatic.com",
    crossOrigin: "anonymous",
  },
  {
    rel: "stylesheet",
    href: "https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&family=IBM+Plex+Mono:ital,wght@0,400;0,500;0,600;1,400;1,500;1,600&family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap",
  },
];

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <Meta />
        <Links />
      </head>
      <body suppressHydrationWarning>
        {children}
        <ScrollRestoration />
        <Scripts />
      </body>
    </html>
  );
}

import { QueryClient, QueryClientProvider, QueryCache, MutationCache } from "@tanstack/react-query";
import { AuthProvider } from "@clients/api/modules/phantom-token-handler-secured-api-client/AuthContext";
import { useState } from "react";
import { Toaster } from "sonner";
import { ThemeProvider } from "next-themes";
import { SessionExpiredError } from "@clients/api/modules/phantom-token-handler-secured-api-client/utilities/sessionExpiredError";
import { SessionExpiredView } from "~/modules/auth/views/SessionExpiredView";
import { ErrorView } from "~/modules/shared/components/ErrorView";

export default function App() {
  const [queryClient] = useState(() => new QueryClient({
    queryCache: new QueryCache({
      onError: (error) => {
        if (error instanceof SessionExpiredError) {
          window.location.href = '/';
        }
      },
    }),
    mutationCache: new MutationCache({
      onError: (error) => {
        if (error instanceof SessionExpiredError) {
          window.location.href = '/';
        }
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000,
        retry: (failureCount, error) => {
          if (error instanceof SessionExpiredError) return false;
          return failureCount < 1;
        },
      },
      mutations: {
        retry: false,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <Toaster />
      <AuthProvider>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <Outlet />
        </ThemeProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export function ErrorBoundary({ error }: Route.ErrorBoundaryProps) {
  let message = "Oops!";
  let details = "An unexpected error occurred.";
  let stack: string | undefined;

  if (isRouteErrorResponse(error)) {
    message = error.status === 404 ? "404" : "Error";
    details =
      error.status === 404
        ? "The requested page could not be found."
        : error.statusText || details;
  } else if (error && error instanceof SessionExpiredError) {
    return <SessionExpiredView />;
  }

  return <ErrorView message={message} details={details} />;
}
