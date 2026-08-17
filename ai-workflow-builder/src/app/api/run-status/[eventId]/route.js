import fs from "fs/promises";

export async function GET(request, { params }) {
  const { eventId } = await params;

  try {
    const content = await fs.readFile(`run-results/${eventId}.json`, "utf-8");
    const data = JSON.parse(content);
    return Response.json({ status: "Completed", ...data });
  } catch {
    return Response.json({ status: "pending" });
  }
}