/**
 * By default, React Router will create a server-side entry point for you.
 *
 * This file (app/entry.server.tsx) overwrites the default entry point.
 * It is required for Bun/Edge environments where `renderToPipeableStream`
 * (from react-dom/server) is not available, but `renderToReadableStream` is.
 */

import { isbot } from "isbot";
import { renderToReadableStream } from "react-dom/server.edge";
import type { AppLoadContext, EntryContext } from "react-router";
import { ServerRouter } from "react-router";

export default async function handleRequest(
    request: Request,
    responseStatusCode: number,
    responseHeaders: Headers,
    routerContext: EntryContext,
    loadContext: AppLoadContext
) {
    let shellRendered = false;
    const userAgent = request.headers.get("user-agent");

    const stream = await renderToReadableStream(
        <ServerRouter context={routerContext} url={request.url} />,
        {
            signal: request.signal,
            onError(error: unknown) {
                responseStatusCode = 500;
                // Log streaming rendering errors from inside the shell
                if (shellRendered) {
                    console.error(error);
                }
            },
        }
    );
    shellRendered = true;

    if (isbot(userAgent)) {
        await stream.allReady;
    }

    responseHeaders.set("Content-Type", "text/html");
    return new Response(stream, {
        status: responseStatusCode,
        headers: responseHeaders,
    });
}
