# Word Lists — IT-deck vocabulary roadmap

Curated vocabulary reference — words and phrases planned for the IT-deck.
Each section is a potential card block. Checked off = cards already exist.

---

## Code review

Phrases used during code review in PRs and comments.

### Reactions / status
- LGTM — Looks Good To Me (approval shorthand)
- nit / nitpick — minor stylistic comment, not a blocker
- blocker — issue that must be fixed before merge
- out of scope — not relevant to this PR, track separately
- let's defer this — postpone to a later PR / sprint
- approved — review passed
- request changes — review failed, needs revision
- nice catch — good spot of a bug or issue

### Suggesting changes
- I'd suggest... — soft recommendation
- consider using... — alternative approach suggestion
- this could be simplified — hint that code is too complex
- I'd extract this into a function — refactoring suggestion
- consider an early return here — control flow suggestion
- I'd rename this to... — naming suggestion
- naming could be clearer — vague naming feedback
- this logic is duplicated — DRY violation
- we already have a utility for this — avoid reinventing
- this is over-engineered — too complex for the problem
- premature optimization — optimizing before it matters (YAGNI)

### Raising concerns
- this breaks the contract — violates an API or interface agreement
- tight coupling here — two things depend on each other too directly
- this could be a performance issue — potential bottleneck
- potential memory leak — resource not released
- magic number — hardcoded value with no explanation
- dead code — unreachable or unused code
- missing test coverage — no tests for this path
- edge case not handled — specific input scenario not covered
- breaking change / non-breaking change — changes API compatibility or not
- this needs documentation — missing explanation for future readers

### Workflow phrases
- let's track this in a separate PR / ticket — scope management
- addressing in a separate PR — deferring a concern
- I'll leave this as a follow-up — not blocking, but noted
- can you add a test for this? — missing test request
- what happens when X? — question about edge case
- have you considered Y? — alternative approach question
- pushing a fix — saying you've committed the correction
- addressed your comment — responded to review feedback

---

## Stand-up / Agile

### Daily stand-up phrases
- I'm on it — I'm currently working on it
- picking this up — starting this task now
- wrapping up — almost done
- blocked on — cannot continue because of X
- waiting for — depends on someone / something else
- good to go — ready, no blockers
- unblocked — blocker was resolved
- I'll take a look — committing to investigate

### Status / progress
- in progress — currently being worked on
- backlogged — in the backlog, not yet started
- carry over — task moves to next sprint unfinished
- shipped / merged / deployed — done and in production
- done done — truly finished (including tests, docs, review)
- ETA — Estimated Time of Arrival (when will it be done?)
- EOD — End of Day
- EOW — End of Week

### Planning / estimation
- story points — abstract unit of effort
- estimate / effort — how much work something takes
- velocity — how much the team gets done per sprint
- capacity — how much bandwidth the team has this sprint
- spike — time-boxed research task to reduce uncertainty
- proof of concept / PoC — minimal prototype to test an idea
- timebox — fixed time limit for a task, stop when time is up
- stretch goal — optional goal if time allows
- must have vs nice to have — priority classification
- scope creep / feature creep — unplanned growth of scope
- quick win / low-hanging fruit — easy task with visible impact
- runway — how much time / work is left before a deadline

### Ceremonies
- grooming / refinement — team reviews and clarifies backlog items
- planning session — sprint planning meeting
- retro / retrospective — team reflects on the sprint
- action item — task assigned during a meeting
- follow-up — something to be done after the meeting
- parking lot — ideas/topics deferred during a meeting
- takeaway — key thing to remember or do after a discussion

### Ticket / task management
- acceptance criteria — conditions for a ticket to be "done"
- definition of done / DoD — team-agreed quality checklist
- P0 / P1 / P2 — priority level (P0 = highest)
- deprioritize — move lower in priority
- open a separate ticket — track something independently
- close as won't fix / out of scope — rejecting a ticket

---

## Incident response

### Severity / classification
- incident — an unexpected event affecting users or systems
- outage / downtime — complete service unavailability
- degradation / partial outage — reduced performance or partial failure
- SEV1 / SEV2 / P0 — severity levels (SEV1 = most critical)
- we're on fire — informal: critical incident in progress
- all hands on deck — everyone should help

### Process
- triage — assess the situation and prioritize
- escalate — involve someone with more authority or expertise
- war room — focused crisis-response meeting (physical or virtual)
- on-call — person responsible to respond to alerts
- runbook / playbook — step-by-step instructions for handling an incident
- postmortem / post-incident review — analysis after an incident is resolved
- timeline / sequence of events — chronological log of what happened
- incident log — running record during the incident

### Metrics
- MTTR — Mean Time To Recover (how long to fix)
- MTTD — Mean Time To Detect (how long to notice)
- MTTF — Mean Time To Failure
- SLA — Service Level Agreement (contractual uptime/performance promise)
- SLO — Service Level Objective (internal target)
- error budget — how much failure is acceptable within SLA
- SLA breach — SLA target was missed

### Response actions
- mitigation — action that reduces impact without full fix
- workaround — temporary fix that bypasses the root cause
- rollback — revert to previous version
- hotfix / emergency deploy — urgent fix pushed outside normal process
- blast radius — scope of users / systems affected
- customer impact — effect on end users

### Analysis
- root cause — the underlying reason the incident happened
- contributing factor — something that made it worse but wasn't the root cause
- immediate cause — the direct trigger
- underlying issue / systemic issue — deeper structural problem
- band-aid fix — temporary fix that doesn't solve the root cause
- prevent recurrence — long-term action to avoid repetition
- action items from postmortem — follow-up tasks after the review

### Comms
- status page — public page showing system health
- stakeholder update — communication to interested parties
- all clear — incident resolved, system stable

---

## Architecture discussions

### Design principles
- separation of concerns — each part does one thing
- single responsibility — a class/module has one reason to change
- tight coupling / loose coupling — degree of dependency between components
- high cohesion — related things are grouped together
- DRY — Don't Repeat Yourself
- SOLID — set of OOP design principles
- YAGNI — You Ain't Gonna Need It (don't build for hypotheticals)
- KISS — Keep It Simple, Stupid

### Scalability
- horizontal scaling / scale out — add more instances
- vertical scaling / scale up — add more resources to one instance
- bottleneck — part of the system that limits overall throughput
- single point of failure / SPOF — one failure brings everything down
- fault tolerance — system keeps working despite partial failure
- graceful degradation — system loses functionality gracefully under stress
- failover — automatic switch to backup
- redundancy — duplication to handle failures
- load balancing — distribute traffic across instances

### Distributed systems
- CAP theorem — Consistency, Availability, Partition tolerance (pick 2)
- eventual consistency — data will be consistent, but not immediately
- strong consistency — data is always immediately consistent
- at-least-once delivery — messages may be delivered more than once
- exactly-once delivery — each message delivered exactly once
- idempotency / idempotent — applying the same operation multiple times = same result
- stateless — no stored session state between requests
- stateful — state is maintained between requests
- shared state — state accessible to multiple services/processes

### Patterns
- event-driven — components communicate via events
- message queue / message broker — async communication via queue
- pub/sub — publisher sends events, subscribers receive
- circuit breaker — stops calling a failing service to prevent cascade
- API gateway — single entry point for all client requests
- service mesh — infrastructure layer managing service-to-service communication
- sidecar — helper container alongside the main one
- CQRS — separate commands (writes) from queries (reads)
- event sourcing — store events, not current state
- saga pattern — managing distributed transactions
- bounded context — DDD concept: a domain boundary

### Data / storage
- sharding / partitioning — splitting data across nodes
- replication — copying data to multiple nodes
- consistency — data is the same across nodes
- ACID — Atomicity, Consistency, Isolation, Durability
- schema migration — changing database structure
- cache invalidation — when to remove/update cached data
- cache-aside / write-through — caching strategies
- connection pooling — reusing DB connections
- N+1 query problem — inefficient repeated queries

### Trade-offs
- trade-off — choosing between two options that each have a cost
- cost vs benefit — weighing investment against value
- build vs buy — make it internally or use a third-party solution
- short-term vs long-term — immediate fix vs sustainable solution
- complexity vs flexibility — simple but rigid vs complex but adaptable

---

## Performance & observability

### Performance concepts
- throughput — amount of work done per unit of time
- latency — delay between request and response
- p50 / p95 / p99 — percentile latency measurements
- jitter — variation in latency
- tail latency — worst-case latency at high percentiles
- benchmark — controlled performance measurement
- profiling — identifying where time/resources are spent
- flame graph — visualization of profiling data
- memory leak — memory allocated but never freed
- garbage collection / GC — automatic memory reclaiming
- GC pressure — too much time spent on garbage collection

### Optimization
- lazy loading — load only when needed
- eager loading — preload to avoid later delay
- batching — group operations together
- pagination — split large results into pages
- compression — reduce data size
- connection pooling — reuse existing connections
- query optimization — make DB queries faster
- index — data structure for fast lookups

### Monitoring / observability
- observability — ability to understand system internals from outputs
- three pillars of observability — logs, metrics, traces
- metric — a numeric measurement over time
- dashboard — visual display of metrics
- alert / alerting — notification when metric crosses threshold
- threshold — limit that triggers an alert
- anomaly — unusual pattern in metrics
- baseline — normal expected value
- SLO — performance target
- error budget — how many errors/failures are acceptable
- telemetry — automated collection of data from a system
- tracing / distributed tracing — following a request across services
- span — a single unit of work in a trace
- correlation ID — ID to link related logs/events across services
- false positive — alert fired when nothing is actually wrong
- flaky alert — alert that fires unreliably
- on-call rotation — schedule for who handles alerts

---

## Technical terms (nouns)

### Concurrency
- race condition — outcome depends on unpredictable order of operations
- deadlock — two processes wait for each other indefinitely
- livelock — processes keep changing but make no progress
- mutex — mutual exclusion lock (only one thread at a time)
- semaphore — controls access to a resource by multiple threads
- lock contention — threads competing for the same lock
- thread-safe — code that works correctly with concurrent execution
- atomic operation — operation that completes without interruption

### API / integration
- endpoint — specific URL for an API operation
- payload — data body of a request or response
- request body — data sent with a POST/PUT request
- response — what the server sends back
- header — metadata in HTTP request/response
- status code — numeric HTTP response code (200, 404, 500...)
- REST — architectural style for APIs
- GraphQL — query language for APIs
- gRPC — high-performance RPC framework
- contract — agreed interface between services
- webhook — HTTP callback triggered by an event
- middleware — software layer between components

### Reliability
- retry — try an operation again after failure
- timeout — maximum wait time before giving up
- fallback — backup behavior when main path fails
- backoff — wait longer between each retry attempt
- exponential backoff — wait time doubles each retry
- rate limit / throttle — restrict number of requests per time period
- circuit breaker — stops requests to a failing service
- bulkhead — isolate failures to prevent cascade

### Code structure
- dependency — something a module relies on
- coupling — degree of dependency between components
- cohesion — how related the parts of a module are
- scope — range of visibility/effect of a variable or function
- constraint — a rule or limit applied to data or behavior
- immutable — cannot be changed after creation
- idempotent — same result no matter how many times applied
- stateless — no memory between calls
- abstraction — hiding complexity behind a simpler interface
- encapsulation — keeping internals private

### DevOps
- container — isolated runtime environment (Docker)
- image — snapshot of a container filesystem
- pod — smallest deployable unit in Kubernetes
- deployment — declaration of desired app state in Kubernetes
- rollout — gradual deployment to production
- canary deployment — release to small % of users first
- blue-green deployment — two identical environments, swap traffic
- feature flag / feature toggle — turn features on/off without deploy
- artifact — build output (JAR, Docker image, binary)
- pipeline — automated sequence of build/test/deploy steps
- CI/CD — Continuous Integration / Continuous Deployment

### Version control
- cherry-pick — apply a specific commit to another branch
- squash — combine multiple commits into one
- rebase — replay commits on top of another branch
- diff — difference between two versions
- patch — set of changes to apply to code
- changeset — group of related changes
- fork — copy of a repository for independent development
- PR / MR — Pull Request / Merge Request

---

## Phrasal verbs

### Infrastructure / deployment
- spin up — start a new instance or environment
- spin down / tear down — shut down and remove
- roll out — gradually deploy to users
- roll back — revert to a previous version
- cut over — switch traffic from old to new system
- phase out / sunset — gradually remove a feature or service
- ramp up — gradually increase (traffic, users, load)
- ramp down — gradually decrease

### Work / tasks
- kick off — start a project or meeting
- wrap up — finish, bring to a close
- pick up — take on a task
- hand off / hand over — transfer responsibility to someone else
- sign off — approve and finish involvement
- take on — accept responsibility for
- push back — delay or object to something
- hold off — wait, don't do it yet
- hold back — restrain or delay
- carry over — move unfinished work to next period
- park / table — defer a topic for later

### Code / debugging
- step through — debug line by line
- drill down — go deeper into details
- zoom out / zoom in — change level of abstraction
- break down — decompose into smaller parts
- clean up — remove unused or messy code
- mock up — create a rough prototype
- write up — document in writing
- read through — carefully review
- run through — go through quickly

### Communication
- loop in — include someone in a conversation
- reach out — contact someone
- circle back — return to a topic later
- flag up / flag — raise attention to an issue
- follow up — check on something after an initial discussion
- check in — get a status update
- sync up — align / talk quickly
- take offline — discuss outside the main meeting

### Other useful
- tap into — make use of a resource or opportunity
- scope out — investigate before committing
- build up — accumulate over time
- burn through — use up quickly
- bridge the gap — connect two things that are disconnected

---

## Meeting / communication phrases

### Aligning
- let's get on the same page — make sure everyone understands equally
- level set — establish a shared starting point
- align on — agree on
- are we aligned? — does everyone agree?
- I want to make sure we're aligned — checking for agreement

### Moving the conversation
- let's take this offline — discuss separately, not in this meeting
- let's park that — set aside for later
- let's circle back to this — return to the topic later
- let's table this — defer (US: postpone; UK: bring to the table = discuss now)
- let's loop in X — include someone who should be part of this
- heads up — informal advance notice
- FYI / for your awareness — informing without requiring action
- for the record — stating something formally

### Decisions
- we need to make a call — a decision is needed
- let's move forward with X — decision made, going with option X
- I'll defer to you on this — you decide, I trust your judgement
- let's not over-engineer this — keep it simple
- this is a blocker — cannot proceed without resolving this

### Status updates
- here's where we are — current situation summary
- quick update — brief status report
- to recap — summary of what was said
- next steps — what happens after this meeting
- action items — tasks assigned with owners
- owner — person responsible for a task
- due by — deadline for an action item

---

## Priorities for card creation

Rough order based on daily usefulness:

1. **Stand-up / planning** — used every single working day
2. **Code review phrases** — multiple PRs per week
3. **Meeting / communication** — daily collaboration
4. **Incident response** — critical when on-call or during outages
5. **Architecture discussions** — design sessions, tech reviews
6. **Technical terms (nouns)** — passive recognition mostly, but some are active
7. **Performance & observability** — useful but more specialized
8. **Phrasal verbs** — ongoing, can mix into other blocks
