Title: Musings on Building a Generative AI Product

URL Source: https://www.linkedin.com/blog/engineering/generative-ai/musings-on-building-a-generative-ai-product

Markdown Content:
Over the last six months, our team here at LinkedIn has been working hard to develop a new AI-powered experience. We wanted to reimagine how our members go about their job searches and browse professional content.

The explosion of generative AI made us pause and consider what was possible now that wasn’t a year ago. We tried many ideas which didn’t really click, eventually discovering the power of turning every feed and job posting into a springboard to:

*   _Get information faster_, e.g. takeaways from a post or learn about the latest from a company.
*   _Connect the dots_, e.g. assess your fit for a job posting.
*   _Receive advice_, e.g. improve your profile or prepare for an interview.
*   And [much more](https://www.linkedin.com/pulse/celebrating-1-billion-members-our-new-ai-powered-linkedin-tomer-cohen-26vre/?trackingId=Rxpg%2FekYRYiyM8mcozYM%2FA%3D%3D)…  
    

**Was it easy to build? What went well and what didn’t?** Building on top of generative AI wasn’t all smooth sailing, and we hit a wall in many places. We want to pull back the “engineering” curtain and share what came easy, where we struggled, and what’s coming next.

Overview
--------

Let’s walk through a real-life scenario to show how the system works.

Imagine you're scrolling through your LinkedIn feed and stumble upon an intriguing post about accessibility in design. Alongside the post, you're presented with a few starter questions to delve deeper into the topic. You're curious and click on, "What are some examples of accessibility driving business value in tech companies?"

Here’s what happens in the background:

1.  **Pick the right agent**: This is where your journey begins. Our system takes your question and decides which AI agent is best equipped to handle it. In this case, it recognizes your interest in accessibility within tech companies and routes your query to an AI agent specialized in general knowledge seeking questions.
2.  **Gather information**: It’s time for some legwork. The AI agent calls a combination of internal APIs & Bing, searching for specific examples and case studies that highlight how accessibility in design has contributed to business value in tech. We are creating a dossier to ground our response.
3.  **Craft a response**: With the necessary information in hand, the agent can now write a response. It filters and synthesizes the data into a coherent, informative answer, providing you with clear examples of how accessibility initiatives have driven business value for tech companies. To avoid generating a wall of text and make the experience more interactive, internal APIs are invoked to decorate the response with attachments like article links, or profiles of people mentioned in the post.

You might follow up with “How do I pivot my career towards this area?”, and we’d repeat the process but now routing you to a career and job AI agent. With just a few clicks you can go deep on any topic, get actionable insights or find your next big opportunity.

Most of this was made possible by the advent of large language models (LLMs), and we thought it’d be interesting to share the behind-the-scenes stories about the challenges we faced building on top of them.

What came easy
--------------

### Overall design

Figure 1: Simplified pipeline for handling user queries. KSA stands for “Knowledge Share Agent”, one of the dozens of agents that can handle user queries

Some of you might’ve noticed from the explanation above that our pipeline follows what’s known as Retrieval Augmented Generation (RAG), which is a common design pattern with generative AI systems. Building the pipeline was surprisingly less of a headache than we anticipated. In just a few days we had the basic framework up and running:

*   **Routing**: decides if the query is in scope or not, and which AI agent to forward it to. Examples of agents are: job assessment, company understanding, takeaways for posts, etc.
*   **Retrieval**: recall-oriented step where the AI agent decides which services to call and how (e.g. LinkedIn People Search, Bing API, etc.).
*   **Generation**: precision-oriented step that sieves through the noisy data retrieved, filters it and produces the final response.

Tuning ‘routing’ and ‘retrieval’ felt more natural given their classification nature: we built dev sets and fitted them with prompt engineering and in-house models. Now, generation, that was a different story. It followed the 80/20 rule; getting it 80% was fast, but that last 20% took most of our work. When the expectation from your product is that 99%+ of your answers should be great, even using the most advanced models available still requires a lot of work and creativity to gain every 1%.

**What worked for us**:

*   Fixed 3-step pipeline
*   Small models for routing/retrieval, bigger models for generation
*   Embedding-Based Retrieval (EBR) powered by an in-memory database as our 'poor man's fine-tuning' to inject response examples directly into our prompts
*   Per-step specific evaluation pipelines, particularly for routing/retrieval

### Development speed

We wanted to move fast across multiple teams and hence decided to split tasks into independent agents (i.e., AI agents) developed by different people: general knowledge, job assessment, post takeaways, etc.

However, this approach introduces a significant compromise. By parallelizing tasks, we gained in terms of speed, but it came at the cost of fragmentation. Maintaining a uniform user experience became challenging when subsequent interactions with an assistant might be managed by varied models, prompts, or tools.

To address this, we adopted a simple organizational structure:

*   A small ‘horizontal’ engineering pod that handled common components and focused on the holistic experience. This included:
    *   The service hosting the product
    *   Tooling for evaluation/testing
    *   Global prompt templates that were consumed by all verticals (e.g. agent’s global identity, conversation history, jailbreak defense, etc.)
    *   Shared UX components for our iOS/Android/Web clients
    *   A server driven UI framework for releasing new UI changes without client code changes or releases.
*   Several ‘vertical’ engineering pods with autonomy on their agents, examples:
    *   Personalized post summarization
    *   Job fit assessment
    *   Interview tips

**What worked for us**:

*   Divide and conquer but limiting the number of agents
*   A centralized evaluation pipeline with multi-turn conversations
*   Sharing prompt templates (e.g. ‘identity’ definition), UX templates, tooling & instrumentation

Where we struggled
------------------

### Evaluation

Evaluating the quality of our answers turned out to be more difficult than anticipated. The challenges can be broadly categorized into three areas: developing guidelines, scaling annotation, and automatic evaluation.

*   **_Developing guidelines_** was the first hurdle. Let’s take Job Assessment as an example: clicking “Assess my fit for this job” and getting “You are a terrible fit” isn’t very useful. We want it to be factual but also empathetic. Some members may be contemplating a career change into fields where they currently do not have a strong fit, and need help understanding what are the gaps and next steps. Ensuring these details were consistent was key for the uniformity of our annotator scores.
*   **_Scaling annotation_** was the second step. Initially everyone in the team chimed in (product, eng, design, etc.), but we knew we needed a more principled approach with consistent and diverse annotators. Our internal linguist team built tooling and processes by which we could _evaluate up to 500 daily conversations_ and get metrics around: overall quality score, hallucination rate, Responsible AI violation, coherence, style, etc. This became our main signpost to understand trends, iterate on prompts & ensure we were ready to go live.
*   **_Automatic evaluation_** is the holy grail, but still a work in progress. Without it, engineers are left with eye-balling results and testing on a limited set of examples, and having a 1+ day delay to know metrics. We are building model-based evaluators to estimate the above metrics & allow for much faster experimentation, and had some success on hallucination detection (but it wasn’t easy!).

Figure 2: Evaluation steps we perform. Engineers perform fast, coarse evaluations to get directional metrics. Annotators give more granular feedback but have a ~1 day turnaround. Members are the final judges and give us scale, but some metrics can take 3+ days for a single change

**What we are working on**: end-to-end automatic evaluation pipeline for faster iteration.

### Calling internal APIs

LinkedIn has a lot of unique data about people, companies, skills, courses, etc. which are critical to building a product offering unique and differentiated value. LLMs, however, have not been trained with this information and hence are unable to use them as is for reasoning and generating responses. A standard pattern to work around this is to set up a Retrieval Augmented Generation (RAG) pipeline, via which internal APIs are called, and their responses are injected into a subsequent LLM prompt to provide additional context to ground the response.

A lot of this unique data is exposed internally via RPC APIs across various microservices. While this is very convenient for humans to invoke programmatically, it is not very LLM friendly. We worked around this by wrapping “skills” around these APIs. Every skill has the following components:

*   A human (and hence LLM) friendly description of what the API does, and when to use it.
*   The configuration to call the RPC API (Endpoint, input schema, output schema etc.)
*   The LLM friendly input and output schema
    *   Primitive typed (String/Boolean/Number) values
    *   JSON schema style input and output schema descriptions
*   The business logic to map between LLM friendly schemas and actual RPC schemas.  
    

Skills like this enable the LLM to do various things relevant to our product like view profiles, search articles/people/jobs/companies and even query internal analytics systems. The same technique is also used for calling non-LinkedIn APIs like Bing search and news.

Figure 3: Calling internal APIs using skills

We write prompts that ask the LLM to decide what skill to use to solve a particular job (skill selection via planning), and then also output the parameters to invoke the skill with (function call). Since the parameters to the call have to match the input schema, we ask the LLM to output them in a structured manner. Most LLMs are trained on YAML and JSON for structured output. We picked YAML because it is less verbose, and hence consumes fewer tokens than JSON.

One of the challenges we ran into was that while about ~90% of the time, the LLM responses contained the parameters in the right format, ~10% of the time the LLM would make mistakes and often output data that was invalid as per the schema supplied, or worse not even valid YAML. These mistakes, while being trivial for a human to spot, caused the code parsing them to barf. ~10% was a high enough number for us to not ignore trivially, and hence we set out to fix this problem.

A standard way to fix this problem is to detect it and then re-prompt the LLM to ask it to correct its mistakes with some additional guidance. While this technique works, it adds a non-trivial amount of latency and also consumes precious GPU capacity due to the additional LLM call. To circumvent these limitations, we ended up writing an in-house defensive YAML parser.

Through an analysis of various payloads, we determined common mistakes made by the LLM, and wrote code to detect and patch these appropriately before parsing. We also modified our prompts to inject hints around some of these common mistakes, to improve the accuracy of our patching. We were ultimately able to reduce occurrences of these errors to ~0.01%.

**What we are working on**: a unified skill registry to dynamically discover and invoke APIs/agents packaged as LLM friendly skills across our generative AI products.

### Consistent quality

The team achieved 80% of the basic experience we were aiming to provide within the first month and then spent an additional four months attempting to surpass 95% completion of our full experience - as we worked diligently to refine, tweak and improve various aspects. We underestimated the challenge of detecting and mitigating hallucinations, as well as the rate at which quality scores improved—initially shooting up, then quickly plateauing.

For product experiences that tolerate such a level of errors, building with generative AI is refreshingly straightforward. But it also creates unattainable expectations, the initial pace created a false sense of ‘almost there,’ which became discouraging as the rate of improvement slowed significantly for each subsequent 1% gain.

Building the assistant felt like a departure from more ‘principled’ ML, and more akin to tweaking rules in expert systems. So while our evaluation became more and more sophisticated, our ‘training’ was mostly prompt engineering which was more of [an art than a science](https://www.microsoft.com/en-us/research/blog/the-power-of-prompting/).

**What we are working on**: fine tuning large language models (LLMs) to make our pipeline more data-driven.

### Capacity & Latency

Capacity and perceived member latency were always top of mind. Some dimensions:

*   **Quality vs Latency**: techniques like Chain of Thought (CoT) are very effective at improving quality and reducing hallucinations. But they require tokens that the member never sees, hence increasing their perceived latency.
*   **Throughput vs Latency**: when running large generative models, it’s often the case that TimeToFirstToken (TTFT) & TimeBetweenTokens (TBT) increase with utilization. In the case of TBT it can sometimes be linear. It’s not uncommon to get 2x/3x the TokensPerSecond (TPS) if you are willing to sacrifice both of those metrics, but we initially had to bound them pretty tight.
*   **Cost**: GPU clusters are not easy to come by and are costly. At the beginning we even had to set timetables for when it was ok to test the product or not, as it’d consume too many tokens and lock out developers from working.
*   **End to end streaming**: a full answer might take minutes to complete, so we make all our requests stream to reduce perceived latency. What’s more, we actually stream within our pipeline end to end. For example the LLM response deciding which APIs to call is progressively parsed and we _fire API calls as soon as parameters are ready_, without waiting for the full LLM response. The final synthesized response is also streamed all the way to the client using our [realtime messaging infrastructure](https://www.linkedin.com/blog/engineering/archive/instant-messaging-at-linkedin-scaling-to-hundreds-of-thousands-) with incremental processing for things like trust/Responsible AI classification.
*   **Async non-blocking pipeline**: Since LLM calls can take a long time to process, we optimized our service throughput by building a fully async non-blocking pipeline that does not waste resources on account of threads blocked on I/O.   
    

These sometimes had an interesting interplay between them. As an example, we initially only bounded TTFT as that mapped to member latency directly for our initial product. As we tackled hallucinations and Chain of Thought became prominent in our prompts, we neglected that TBT would hurt us much more, as any ‘reasoning’ token would multiple member latency (e.g. for a 200-token reasoning step, even a 10ms TBT increase means an extra 2s of latency). This caused one of our public ramps to suddenly sound alerts left and right that some tasks were hitting timeouts, and we quickly had to increase capacity to alleviate the issue.

**What we are working on**:

*   Moving simpler tasks to in-house, fine-tuned models.
*   More predictable deployment infrastructure for LLM deployments.
*   Reducing wasted tokens of every step.

Takeaways
---------

Enough from us, why don’t we let the product do the talking?

That’s not bad! The follow-up suggestions, in particular, can lead you down a Wikipedia-style rabbit hole of curiosity.

As we continue to refine quality, develop new features, and optimize the pipeline for speed, we'll be rolling out to more users very soon.

Getting here has been a monumental effort from a wonderful group of people, and we’ll be sharing more technical details soon as we keep learning. Stay tuned!
