import { createVertex } from "@ai-sdk/google-vertex";
import { createEdgeRuntimeAPI } from "@assistant-ui/react/edge";

export const { POST } = createEdgeRuntimeAPI({
  model: createVertex({
    project: 'boris001',
    location: 'us-central1'
  })("gemini-1.5-flash")
});
