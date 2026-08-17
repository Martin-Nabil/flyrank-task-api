import { inngest } from "./client";
import OpenAI from "openai";

const client = new OpenAI({
  baseURL: process.env.LLM_BASE_URL,
  apiKey: process.env.LLM_API_KEY,
});

async function askYesNo(prompt) {
  const response = await client.chat.completions.create({
    model: process.env.LLM_MODEL,
    temperature: 0,
    messages: [
      {
        role: "system",
        content:
          "You are a decision node in a workflow. Answer the question with exactly one word: YES or NO. No other text, no punctuation, no explanation.",
      },
      { role: "user", content: prompt },
    ],
  });

  const raw = response.choices[0].message.content.trim().toUpperCase();
  return raw.includes("YES") ? "YES" : "NO";
}

export const runWorkflow = inngest.createFunction(
  { id: "run-workflow", triggers: { event: "workflow/run" } },
  async ({ event, step }) => {
    const { nodes, edges, startNodeId } = event.data;

    const executionLog = [];
    let currentNodeId = startNodeId;
    const visited = new Set();

    while (currentNodeId && !visited.has(currentNodeId)) {
      visited.add(currentNodeId);

      const currentNode = nodes.find((n) => n.id === currentNodeId);
      if (!currentNode) break;

      const answer = await step.run(`node-${currentNodeId}`, async () => {
        const result = await askYesNo(currentNode.data.label);
        return result;
      });

      executionLog.push({
        nodeId: currentNodeId,
        prompt: currentNode.data.label,
        answer,
      });

      const nextEdge = edges.find(
        (e) => e.source === currentNodeId && e.data?.branch === answer
      );

      currentNodeId = nextEdge ? nextEdge.target : null;
    }

    return { executionLog };
  }
);