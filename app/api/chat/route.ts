import { vertex } from "@ai-sdk/google-vertex";
import { createEdgeRuntimeAPI } from "@assistant-ui/react/edge";
 
export const { POST } = createEdgeRuntimeAPI({
  model: vertex("gemini-1.5-pro"),
});