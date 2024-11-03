import { createVertex } from "@ai-sdk/google-vertex";
import { createEdgeRuntimeAPI } from "@assistant-ui/react/edge";

export const { POST } = createEdgeRuntimeAPI({
  model: createVertex({
    project: process.env.PROJECT_ID,
    location: 'us-central1'
  })("gemini-1.5-flash")
});
