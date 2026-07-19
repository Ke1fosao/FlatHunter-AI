import { proxyApiRequest } from "@/lib/server-api-proxy";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

async function handle(request: Request, context: RouteContext): Promise<Response> {
  const { path } = await context.params;
  return proxyApiRequest(request, path);
}

export function GET(request: Request, context: RouteContext): Promise<Response> {
  return handle(request, context);
}

export function HEAD(request: Request, context: RouteContext): Promise<Response> {
  return handle(request, context);
}

export function POST(request: Request, context: RouteContext): Promise<Response> {
  return handle(request, context);
}

export function PUT(request: Request, context: RouteContext): Promise<Response> {
  return handle(request, context);
}

export function PATCH(request: Request, context: RouteContext): Promise<Response> {
  return handle(request, context);
}

export function DELETE(request: Request, context: RouteContext): Promise<Response> {
  return handle(request, context);
}

export function OPTIONS(request: Request, context: RouteContext): Promise<Response> {
  return handle(request, context);
}
