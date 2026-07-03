I'm a senior full stack JavaScript developer with over seven years of experience.
I build scalable web applications — using React, NestJS and AWS infrastructure.
I started my career as a PHP developer, working with WordPress and Laravel.
Over time I moved into JavaScript — it felt like a natural next step.
At TopDevs and DataArt I worked with React, TypeScript, and Node.js.
For the past four years I've been at The AA, one of the UK's largest brands.
In The AA, I've been leading re-platforming from legacy systems to modern architecture.
I design and build end-to-end features — from frontend to backend.
I also lead code reviews and mentor developers across the team.
Outside of work, I run a YouTube channel focused on engineering and development.
I've recorded over three hundred hours of different topics so far.
I also build open-source tools and use them as teaching material.
I also founded ITFriday — a live tech community for IT.
We stream every Friday and cover everything from the IT world.
I'm now looking for a new challenge where I can bring all of this together.
At The AA I work in an IT department responsible for digital products.
Our team consists of 6 developers, 1 QA engineer, and a product owner.
We work on a variety of apps — from internal tools to customer products.
The backend is built on NestJS with GraphQL and an API gateway pattern.
On the backend we implement new features and fix bugs, not build from scratch.
But on frontend, I design and build applications from scratch.
I also work with some serverless infrastructure to support old applications and design new ones.
When we need some backend functionality, we mostly build serverless functions on AWS Lambda.
I also migrated old NestJS and Apollo modules to their modern versions.
Currently I'm leading a major frontend upgrade from an old React codebase.
The app had legacy MUI, outdated libraries, and was running on Node 16.
I introduced Storybook to prevent duplicate components and silent regressions.
Before that, broken UI changes were only caught during QA testing.
I didn't choose GraphQL — it was already in place when I joined.
But I understand why it was chosen — REST would mean too many endpoints.
Honestly, GraphQL has its own complexity — many resolvers, hard to trace.
Replacing it now would be too costly, so we work with what we have.
We use Lambda for atomic, async operations that don't need instant response.
The result is delivered later — via email or another async mechanism.
NestJS was already the stack when I joined, and I would have chosen it anyway.
It gives us a lot out of the box — architecture patterns and plugin ecosystem.
One of my proudest achievements was building a custom calendar from scratch.
We didn't use any third-party libraries — everything was built in-house.
It gave us full control over behaviour, design, and edge cases.
I introduced Storybook across all UI applications in the team.
It made development faster and testing much more reliable.
Complex multi-step scenarios became easy to isolate and test independently.
Before Storybook, issues in those flows were often missed until regression.
In code reviews I focus on code quality, system impact, and new dependencies.
I always think about how a change might affect other parts of the application.
I also question every new library — do we really need it, or can we avoid it?
Formal mentoring isn't common in my current team — everyone works independently.
Instead, I develop my teaching passion into my YouTube channel and ITFriday.
I've created full series of videos to guide developers who are just starting out.
I started adding Vue to my Laravel projects — it felt like a natural extension.
Then I tried React and immediately preferred it over Vue.
Working in outsourcing meant many projects, and JS simply dominated them all.
Over time I standardised my entire stack around JavaScript.
I've been at The AA for four years and I feel I've grown as much as I can here.
I'm looking for a role with more technical complexity and bigger challenges.
I want to work in an environment where engineering is a core priority.
I genuinely enjoy sharing knowledge — it keeps me sharp and engaged.
Teaching forces you to understand things deeply, not just use them.
My channel covers real engineering problems, not just tutorial content.
ITFriday started as a way to reconnect the Ukrainian IT community abroad.
We stream every Friday and discuss both technical and human topics.
It's grown into something I'm genuinely proud of outside of my day job.



I avoid premature optimization — the code often needs to change later anyway.
First, I ask if a hook is even necessary, or if structure can solve it instead.
Often useCallback isn't needed if you move the function outside the component.
Passing data as props instead of internal state removes the need for it.
useMemo is great for memoising genuinely expensive calculations.
But it's not free — it adds complexity and can complicate testing.
Re-render issues are usually a sign of poor component decomposition.
Breaking components down properly often solves re-render problems naturally.
Reconciliation compares the old virtual DOM tree with the new one.
If there's a difference, React triggers a cascading re-render from that point.


---
I'm sorry, you're kind of breaking up there
If you led the team, what would you change?