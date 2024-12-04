Title: What We Learned from a Year of Building with LLMs (Part III): Strategy

URL Source: https://www.oreilly.com/radar/what-we-learned-from-a-year-of-building-with-llms-part-iii-strategy/

Published Time: 2024-06-06T06:46:19-04:00

Markdown Content:
We [previously shared](https://www.oreilly.com/radar/what-we-learned-from-a-year-of-building-with-llms-part-i/) our insights on the _tactics_ we have honed while operating LLM applications. Tactics are granular: they are the specific actions employed to achieve specific objectives. We [also shared](https://www.oreilly.com/radar/what-we-learned-from-a-year-of-building-with-llms-part-ii/) our perspective on _operations_: the higher-level processes in place to support tactical work to achieve objectives.

[![Image 14](https://d3ansictanv2wj.cloudfront.net/safari-topic-cta-1f60e6f96856da19ba3cb25660472ca5.jpg)](https://www.oreilly.com/online-learning/)

Learn faster. Dig deeper. See farther.
--------------------------------------

But where do those objectives come from? That is the domain of _strategy_. Strategy answers the “what” and “why” questions behind the “how” of tactics and operations.

We provide our opinionated takes, such as “no GPUs before PMF” and “focus on the system not the model,” to help teams figure out where to allocate scarce resources. We also suggest a roadmap for iterating toward a great product. This final set of lessons answers the following questions:

1.  Building vs. Buying: When should you train your own models, and when should you leverage existing APIs? The answer is, as always, “it depends.” We share what it depends on.
2.  Iterating to Something Great: How can you create a lasting competitive edge that goes beyond just using the latest models? We discuss the importance of building a robust system around the model and focusing on delivering memorable, sticky experiences.
3.  Human-Centered AI: How can you effectively integrate LLMs into human workflows to maximize productivity and happiness? We emphasize the importance of building AI tools that support and enhance human capabilities rather than attempting to replace them entirely.
4.  Getting Started: What are the essential steps for teams embarking on building an LLM product? We outline a basic playbook that starts with prompt engineering, evaluations, and data collection.
5.  The Future of Low-Cost Cognition: How will the rapidly decreasing costs and increasing capabilities of LLMs shape the future of AI applications? We examine historical trends and walk through a simple method to estimate when certain applications might become economically feasible.
6.  From Demos to Products: What does it take to go from a compelling demo to a reliable, scalable product? We emphasize the need for rigorous engineering, testing, and refinement to bridge the gap between prototype and production.

To answer these difficult questions, let’s _think step by step…_

Strategy: Building with LLMs without Getting Out-Maneuvered
-----------------------------------------------------------

Successful products require thoughtful planning and tough prioritization, not endless prototyping or following the latest model releases or trends. In this final section, we look around the corners and think about the strategic considerations for building great AI products. We also examine key trade-offs teams will face, like when to build and when to buy, and suggest a “playbook” for early LLM application development strategy.

### No GPUs before PMF

To be great, your product needs to be more than just a thin wrapper around somebody else’s API. But mistakes in the opposite direction can be even more costly. The past year has also seen a mint of venture capital, including an eye-watering six-billion-dollar Series A, spent on training and customizing models without a clear product vision or target market. In this section, we’ll explain why jumping immediately to training your own models is a mistake and consider the role of self-hosting.

#### Training from scratch (almost) never makes sense

For most organizations, pretraining an LLM from scratch is an impractical distraction from building products.

As exciting as it is and as much as it seems like everyone else is doing it, developing and maintaining machine learning infrastructure takes a lot of resources. This includes gathering data, training and evaluating models, and deploying them. If you’re still validating product-market fit, these efforts will divert resources from developing your core product. Even if you had the compute, data, and technical chops, the pretrained LLM may become obsolete in months.

Consider the case of [BloombergGPT](https://arxiv.org/abs/2303.17564), an LLM specifically trained for financial tasks. The model was pretrained on 363B tokens and required a heroic effort by [nine full-time employees](https://twimlai.com/podcast/twimlai/bloomberggpt-an-llm-for-finance/), four from AI Engineering and five from ML Product and Research. Despite this effort, it was [outclassed by gpt-3.5-turbo and gpt-4](https://arxiv.org/abs/2305.05862) on those financial tasks within a year.

This story and others like it suggests that for most practical applications, pretraining an LLM from scratch, even on domain-specific data, is not the best use of resources. Instead, teams are better off fine-tuning the strongest open source models available for their specific needs.

There are of course exceptions. One shining example is [Replit’s code model](https://blog.replit.com/replit-code-v1_5), trained specifically for code-generation and understanding. With pretraining, Replit was able to outperform other models of large sizes such as CodeLlama7b. But as other, increasingly capable models have been released, maintaining utility has required continued investment.

#### Don’t fine-tune until you’ve proven it’s necessary

For most organizations, fine-tuning is driven more by FOMO than by clear strategic thinking.

Organizations invest in fine-tuning too early, trying to beat the “just another wrapper” allegations. In reality, fine-tuning is heavy machinery, to be deployed only after you’ve collected plenty of examples that convince you other approaches won’t suffice.

A year ago, many teams were telling us they were excited to fine-tune. Few have found product-market fit and most regret their decision. If you’re going to fine-tune, you’d better be _really_ confident that you’re set up to do it again and again as base models improve—see the “The model isn’t the product” and “Build LLMOps” below.

When might fine-tuning actually be the right call? If the use case requires data not available in the mostly open web-scale datasets used to train existing models—and if you’ve already built an MVP that demonstrates the existing models are insufficient. But be careful: if great training data isn’t readily available to the model builders, where are _you_ getting it?

Ultimately, remember that LLM-powered applications aren’t a science fair project; investment in them should be commensurate with their contribution to your business’ strategic objectives and its competitive differentiation.

#### Start with inference APIs, but don’t be afraid of self-hosting

With LLM APIs, it’s easier than ever for startups to adopt and integrate language modeling capabilities without training their own models from scratch. Providers like Anthropic and OpenAI offer general APIs that can sprinkle intelligence into your product with just a few lines of code. By using these services, you can reduce the effort spent and instead focus on creating value for your customers—this allows you to validate ideas and iterate toward product-market fit faster.

But, as with databases, managed services aren’t the right fit for every use case, especially as scale and requirements increase. Indeed, self-hosting may be the only way to use models without sending confidential/private data out of your network, as required in regulated industries like healthcare and finance or by contractual obligations or confidentiality requirements.

Furthermore, self-hosting circumvents limitations imposed by inference providers, like rate limits, model deprecations, and usage restrictions. In addition, self-hosting gives you complete control over the model, making it easier to construct a differentiated, high-quality system around it. Finally, self-hosting, especially of fine-tunes, can reduce cost at large scale. For example, [BuzzFeed shared how they fine-tuned open source LLMs to reduce costs by 80%](https://tech.buzzfeed.com/lessons-learned-building-products-powered-by-generative-ai-7f6c23bff376#9da5).

### Iterate to something great

To sustain a competitive edge in the long run, you need to think beyond models and consider what will set your product apart. While speed of execution matters, it shouldn’t be your only advantage.

#### The model isn’t the product; the system around it is

For teams that aren’t building models, the rapid pace of innovation is a boon as they migrate from one SOTA model to the next, chasing gains in context size, reasoning capability, and price-to-value to build better and better products.

This progress is as exciting as it is predictable. Taken together, this means models are likely to be the least durable component in the system.

Instead, focus your efforts on what’s going to provide lasting value, such as:

*   Evaluation chassis: To reliably measure performance on your task across models
*   Guardrails: To prevent undesired outputs no matter the model
*   Caching: To reduce latency and cost by avoiding the model altogether
*   Data flywheel: To power the iterative improvement of everything above

These components create a thicker moat of product quality than raw model capabilities.

But that doesn’t mean building at the application layer is risk free. Don’t point your shears at the same yaks that OpenAI or other model providers will need to shave if they want to provide viable enterprise software.

For example, some teams invested in building custom tooling to validate structured output from proprietary models; minimal investment here is important, but a deep one is not a good use of time. OpenAI needs to ensure that when you ask for a function call, you get a valid function call—because all of their customers want this. Employ some “strategic procrastination” here, build what you absolutely need and await the obvious expansions to capabilities from providers.

#### Build trust by starting small

Building a product that tries to be everything to everyone is a recipe for mediocrity. To create compelling products, companies need to specialize in building memorable, sticky experiences that keep users coming back.

Consider a generic RAG system that aims to answer any question a user might ask. The lack of specialization means that the system can’t prioritize recent information, parse domain-specific formats, or understand the nuances of specific tasks. As a result, users are left with a shallow, unreliable experience that doesn’t meet their needs.

To address this, focus on specific domains and use cases. Narrow the scope by going deep rather than wide. This will create domain-specific tools that resonate with users. Specialization also allows you to be upfront about your system’s capabilities and limitations. Being transparent about what your system can and cannot do demonstrates self-awareness, helps users understand where it can add the most value, and thus builds trust and confidence in the output.

#### Build LLMOps, but build it for the right reason: faster iteration

DevOps is not fundamentally about reproducible workflows or shifting left or empowering two pizza teams—and it’s definitely not about writing YAML files.

DevOps is about shortening the feedback cycles between work and its outcomes so that improvements accumulate instead of errors. Its roots go back, via the Lean Startup movement, to Lean manufacturing and the Toyota Production System, with its emphasis on Single Minute Exchange of Die and Kaizen.

MLOps has adapted the form of DevOps to ML. We have reproducible experiments and we have all-in-one suites that empower model builders to ship. And Lordy, do we have YAML files.

But as an industry, MLOps didn’t adapt the function of DevOps. It didn’t shorten the feedback gap between models and their inferences and interactions in production.

Hearteningly, the field of LLMOps has shifted away from thinking about hobgoblins of little minds like prompt management and toward the hard problems that block iteration: production monitoring and continual improvement, linked by evaluation.

Already, we have interactive arenas for neutral, crowd-sourced evaluation of chat and coding models—an outer loop of collective, iterative improvement. Tools like LangSmith, Log10, LangFuse, W&B Weave, HoneyHive, and more promise to not only collect and collate data about system outcomes in production but also to leverage them to improve those systems by integrating deeply with development. Embrace these tools or build your own.

#### Don’t build LLM features you can buy

Most successful businesses are not LLM businesses. Simultaneously, most businesses have opportunities to be improved by LLMs.

This pair of observations often misleads leaders into hastily retrofitting systems with LLMs at increased cost and decreased quality and releasing them as ersatz, vanity “AI” features, complete with the [now-dreaded sparkle icon](https://x.com/nearcyan/status/1783351706031718412). There’s a better way: focus on LLM applications that truly align with your product goals and enhance your core operations.

Consider a few misguided ventures that waste your team’s time:

*   Building custom text-to-SQL capabilities for your business
*   Building a chatbot to talk to your documentation
*   Integrating your company’s knowledge base with your customer support chatbot

While the above are the hellos-world of LLM applications, none of them make sense for virtually any product company to build themselves. These are general problems for many businesses with a large gap between promising demo and dependable component—the customary domain of software companies. Investing valuable R&D resources on general problems being tackled en masse by the current Y Combinator batch is a waste.

If this sounds like trite business advice, it’s because in the frothy excitement of the current hype wave, it’s easy to mistake anything “LLM” as cutting-edge accretive differentiation, missing which applications are already old hat.

#### AI in the loop; humans at the center

Right now, LLM-powered applications are brittle. They required an incredible amount of safe-guarding and defensive engineering and remain hard to predict. Additionally, when tightly scoped, these applications can be wildly useful. This means that LLMs make excellent tools to accelerate user workflows.

While it may be tempting to imagine LLM-based applications fully replacing a workflow or standing in for a job function, today the most effective paradigm is a human-computer centaur (c.f. [Centaur chess](https://en.wikipedia.org/wiki/Advanced_chess)). When capable humans are paired with LLM capabilities tuned for their rapid utilization, productivity and happiness doing tasks can be massively increased. One of the flagship applications of LLMs, GitHub Copilot, demonstrated the power of these workflows:

> “Overall, developers told us they felt more confident because coding is easier, more error-free, more readable, more reusable, more concise, more maintainable, and more resilient with GitHub Copilot and GitHub Copilot Chat than when they’re coding without it.”  
> —[Mario Rodriguez, GitHub](https://resources.github.com/learn/pathways/copilot/essentials/measuring-the-impact-of-github-copilot/)

For those who have worked in ML for a long time, you may jump to the idea of “human-in-the-loop,” but not so fast: HITL machine learning is a paradigm built on human experts ensuring that ML models behave as predicted. While related, here we are proposing something more subtle. LLM driven systems should not be the primary drivers of most workflows today; they should merely be a resource.

By centering humans and asking how an LLM can support their workflow, this leads to significantly different product and design decisions. Ultimately, it will drive you to build different products than competitors who try to rapidly offshore all responsibility to LLMs—better, more useful, and less risky products.

### Start with prompting, evals, and data collection

The previous sections have delivered a fire hose of techniques and advice. It’s a lot to take in. Let’s consider the minimum useful set of advice: if a team wants to build an LLM product, where should they begin?

Over the last year, we’ve seen enough examples to start becoming confident that successful LLM applications follow a consistent trajectory. We walk through this basic “getting started” playbook in this section. The core idea is to start simple and only add complexity as needed. A decent rule of thumb is that each level of sophistication typically requires at least an order of magnitude more effort than the one before it. With this in mind…

#### Prompt engineering comes first

Start with prompt engineering. Use all the techniques we discussed in the tactics section before. Chain-of-thought, n-shot examples, and structured input and output are almost always a good idea. Prototype with the most highly capable models before trying to squeeze performance out of weaker models.

Only if prompt engineering cannot achieve the desired level of performance should you consider fine-tuning. This will come up more often if there are nonfunctional requirements (e.g., data privacy, complete control, and cost) that block the use of proprietary models and thus require you to self-host. Just make sure those same privacy requirements don’t block you from using user data for fine-tuning!

#### Build evals and kickstart a data flywheel

Even teams that are just getting started need evals. Otherwise, you won’t know whether your prompt engineering is sufficient or when your fine-tuned model is ready to replace the base model.

Effective evals are [specific to your tasks](https://twitter.com/thesephist/status/1707839140018974776) and mirror the intended use cases. The first level of evals that we [recommend](https://hamel.dev/blog/posts/evals/) is unit testing. These simple assertions detect known or hypothesized failure modes and help drive early design decisions. Also see other [task-specific evals](https://eugeneyan.com/writing/evals/) for classification, summarization, etc.

While unit tests and model-based evaluations are useful, they don’t replace the need for human evaluation. Have people use your model/product and provide feedback. This serves the dual purpose of measuring real-world performance and defect rates while also collecting high-quality annotated data that can be used to fine-tune future models. This creates a positive feedback loop, or data flywheel, which compounds over time:

*   Use human evaluation to assess model performance and/or find defects

*   Use the annotated data to fine-tune the model or update the prompt

*   Repeat

For example, when auditing LLM-generated summaries for defects we might label each sentence with fine-grained feedback identifying factual inconsistency, irrelevance, or poor style. We can then use these factual inconsistency annotations to [train a hallucination classifier](https://eugeneyan.com/writing/finetuning/) or use the relevance annotations to train a [reward model to score on relevance](https://arxiv.org/abs/2009.01325). As another example, LinkedIn shared about its success with using [model-based evaluators](https://www.linkedin.com/blog/engineering/generative-ai/musings-on-building-a-generative-ai-product) to estimate hallucinations, responsible AI violations, coherence, etc. in its write-up.

By creating assets that compound their value over time, we upgrade building evals from a purely operational expense to a strategic investment and build our data flywheel in the process.

### The high-level trend of low-cost cognition

In 1971, the researchers at Xerox PARC predicted the future: the world of networked personal computers that we are now living in. They helped birth that future by playing pivotal roles in the invention of the technologies that made it possible, from Ethernet and graphics rendering to the mouse and the window.

But they also engaged in a simple exercise: they looked at applications that were very useful (e.g., video displays) but were not yet economical (i.e., enough RAM to drive a video display was many thousands of dollars). Then they looked at historic price trends for that technology (à la Moore’s law) and predicted when those technologies would become economical.

We can do the same for LLM technologies, even though we don’t have something quite as clean as transistors-per-dollar to work with. Take a popular, long-standing benchmark, like the Massively-Multitask Language Understanding dataset, and a consistent input approach (five-shot prompting). Then, compare the cost to run language models with various performance levels on this benchmark over time.

![Image 15](https://applied-llms.org/images/models-prices.png)

For a fixed cost, capabilities are rapidly increasing. For a fixed capability level, costs are rapidly decreasing. Created by coauthor Charles Frye using public data on May 13, 2024.

In the four years since the launch of OpenAI’s davinci model as an API, the cost for running a model with equivalent performance on that task at the scale of one million tokens (about one hundred copies of this document) has dropped from $20 to less than 10¢—a halving time of just six months. Similarly, the cost to run Meta’s LLama 3 8B via an API provider or on your own is just 20¢ per million tokens as of May 2024, and it has similar performance to OpenAI’s text-davinci-003, the model that enabled ChatGPT to shock the world. That model also cost about $20 per million tokens when it was released in late November 2023. That’s two orders of magnitude in just 18 months—the same time frame in which Moore’s law predicts a mere doubling.

Now, let’s consider an application of LLMs that is very useful (powering generative video game characters, à la [Park et al](https://arxiv.org/abs/2304.03442).) but is not yet economical. (Their cost was estimated at $625 per hour [here](https://arxiv.org/abs/2310.02172).) Since that paper was published in August 2023, the cost has dropped roughly one order of magnitude, to $62.50 per hour. We might expect it to drop to $6.25 per hour in another nine months.

Meanwhile, when _Pac-Man_ was released in 1980, $1 of today’s money would buy you a credit, good to play for a few minutes or tens of minutes—call it six games per hour, or $6 per hour. This napkin math suggests that a compelling LLM-enhanced gaming experience will become economical some time in 2025.

These trends are new, only a few years old. But there is little reason to expect this process to slow down in the next few years. Even as we perhaps use up low-hanging fruit in algorithms and datasets, like scaling past the “Chinchilla ratio” of ~20 tokens per parameter, deeper innovations and investments inside the data center and at the silicon layer promise to pick up slack.

And this is perhaps the most important strategic fact: what is a completely infeasible floor demo or research paper today will become a premium feature in a few years and then a commodity shortly after. We should build our systems, and our organizations, with this in mind.

Enough 0 to 1 Demos, It’s Time for 1 to N Products
--------------------------------------------------

We get it; building LLM demos is a ton of fun. With just a few lines of code, a vector database, and a carefully crafted prompt, we create ✨magic ✨. And in the past year, this magic has been compared to the internet, the smartphone, and even the printing press.

Unfortunately, as anyone who has worked on shipping real-world software knows, there’s a world of difference between a demo that works in a controlled setting and a product that operates reliably at scale.

Take, for example, self-driving cars. The first car was driven by a neural network in [1988](https://proceedings.neurips.cc/paper/1988/file/812b4ba287f5ee0bc9d43bbf5bbe87fb-Paper.pdf). Twenty-five years later, Andrej Karpathy [took his first demo ride in a Waymo](https://x.com/karpathy/status/1689819017610227712). A decade after that, the company received its [driverless permit](https://x.com/Waymo/status/1689809230293819392). That’s thirty-five years of rigorous engineering, testing, refinement, and regulatory navigation to go from prototype to commercial product.

Across different parts of industry and academia, we have keenly observed the ups and downs for the past year: year 1 of N for LLM applications. We hope that the lessons we have learned—from tactics like rigorous operational techniques for building teams to strategic perspectives like which capabilities to build internally—help you in year 2 and beyond, as we all build on this exciting new technology together.

### About the authors

**Eugene Yan** designs, builds, and operates machine learning systems that serve customers at scale. He’s currently a Senior Applied Scientist at Amazon where he builds [RecSys for millions worldwide](https://eugeneyan.com/speaking/recsys2022-keynote/) and applies [LLMs to serve customers better](https://eugeneyan.com/speaking/ai-eng-summit/). Previously, he led machine learning at Lazada (acquired by Alibaba) and a Healthtech Series A. He writes & speaks about ML, RecSys, LLMs, and engineering at [eugeneyan.com](https://eugeneyan.com/) and [ApplyingML.com](https://applyingml.com/).

**Bryan Bischof** is the Head of AI at Hex, where he leads the team of engineers building Magic – the data science and analytics copilot. Bryan has worked all over the data stack leading teams in analytics, machine learning engineering, data platform engineering, and AI engineering. He started the data team at Blue Bottle Coffee, led several projects at Stitch Fix, and built the data teams at Weights and Biases. Bryan previously co-authored the book Building Production Recommendation Systems with O’Reilly, and teaches Data Science and Analytics in the graduate school at Rutgers. His Ph.D. is in pure mathematics.

**Charles Frye** teaches people to build AI applications. After publishing research in [psychopharmacology](https://pubmed.ncbi.nlm.nih.gov/24316346/) and [neurobiology](https://journals.physiology.org/doi/full/10.1152/jn.00172.2016), he got his Ph.D. at the University of California, Berkeley, for dissertation work on [neural network optimization](https://arxiv.org/abs/2003.10397). He has taught thousands the entire stack of AI application development, from linear algebra fundamentals to GPU arcana and building defensible businesses, through educational and consulting work at Weights and Biases, [Full Stack Deep Learning](https://fullstackdeeplearning.com/), and Modal.

**Hamel Husain** is a machine learning engineer with over 25 years of [experience](https://www.linkedin.com/in/hamelhusain/). He has worked with innovative companies such as Airbnb and GitHub, which included [early LLM research used by OpenAI](https://openai.com/index/introducing-text-and-code-embeddings#:~:text=models%20on%20the-,CodeSearchNet,),-evaluation%20suite%20where) for code understanding. He has also led and contributed to numerous popular [open-source machine-learning tools](https://hamel.dev/oss/opensource.html). Hamel is currently an [independent consultant](https://hamel.dev/hire.html) helping companies operationalize Large Language Models (LLMs) to accelerate their AI product journey.

**Jason Liu** is a distinguished machine learning [consultant](https://jxnl.co/services/) known for leading teams to successfully ship AI products. Jason’s technical expertise covers personalization algorithms, search optimization, synthetic data generation, and MLOps systems.

His experience includes companies like Stitch Fix, where he created a recommendation framework and observability tools that handled 350 million daily requests. Additional roles have included Meta, NYU, and startups such as Limitless AI and Trunk Tools.

**Shreya Shankar** is an ML engineer and PhD student in computer science at UC Berkeley. She was the first ML engineer at 2 startups, building AI-powered products from scratch that serve thousands of users daily. As a researcher, her work focuses on addressing data challenges in production ML systems through a human-centered approach. Her work has appeared in top data management and human-computer interaction venues like VLDB, SIGMOD, CIDR, and CSCW.

### Contact Us

We would love to hear your thoughts on this post. You can contact us at [contact@applied-llms.org](mailto:contact@applied-llms.org). Many of us are open to various forms of consulting and advisory. We will route you to the correct expert(s) upon contact with us if appropriate.

### Acknowledgements

This series started as a conversation in a group chat, where Bryan quipped that he was inspired to write “A Year of AI Engineering”. Then, ✨magic✨ happened in the group chat (see image below), and we were all inspired to chip in and share what we’ve learned so far.

The authors would like to thank Eugene for leading the bulk of the document integration and overall structure in addition to a large proportion of the lessons. Additionally, for primary editing responsibilities and document direction. The authors would like to thank Bryan for the spark that led to this writeup, restructuring the write-up into tactical, operational, and strategic sections and their intros, and for pushing us to think bigger on how we could reach and help the community. The authors would like to thank Charles for his deep dives on cost and LLMOps, as well as weaving the lessons to make them more coherent and tighter—you have him to thank for this being 30 instead of 40 pages! The authors appreciate Hamel and Jason for their insights from advising clients and being on the front lines, for their broad generalizable learnings from clients, and for deep knowledge of tools. And finally, thank you Shreya for reminding us of the importance of evals and rigorous production practices and for bringing her research and original results to this piece.

Finally, the authors would like to thank all the teams who so generously shared your challenges and lessons in your own write-ups which we’ve referenced throughout this series, along with the AI communities for your vibrant participation and engagement with this group.

![Image 16](https://eugeneyan.com/assets/how-it-started.jpg)
