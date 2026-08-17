import { inngest } from "../../../inngest/client";

export async function POST(request) {
  const body = await request.json();

  const result = await inngest.send({
    name: "workflow/run",
    data: body,
  });

  return Response.json({ eventId: result.ids[0] });
}