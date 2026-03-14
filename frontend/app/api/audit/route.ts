import { NextResponse } from "next/server";
import { getRouteData } from "@/app/api/_lib/data-source";

export async function GET() {
  return NextResponse.json(await getRouteData("audit"));
}


