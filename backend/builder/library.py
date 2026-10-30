"""Generic topic library the plan builder assembles plans from.

Each topic becomes a track. Each unit has a level:
  1 = foundations, 2 = core working skills, 3 = advanced.
A unit may `requires` another unit (by key) in a different topic; the builder keeps that link
only when both units end up in the plan. Skill names match the Market page.
All resources are free.
"""

from typing import Dict, List, Optional


def r(kind: str, title: str, url: str) -> Dict:
    return {"kind": kind, "title": title, "url": url}


def learn(title: str, minutes: int, tasks: List[str], done_when: str, resources=()) -> Dict:
    return {"kind": "learn", "title": title, "minutes": minutes, "tasks": tasks, "done_when": done_when,
            "resources": list(resources)}


def practice(title: str, minutes: int, tasks: List[str], done_when: str, resources=()) -> Dict:
    return {"kind": "practice", "title": title, "minutes": minutes, "tasks": tasks, "done_when": done_when,
            "resources": list(resources)}


def project(key: str, title: str, difficulty: str, hours: int, description: str, features: List[str],
            stretch: List[str] = ()) -> Dict:
    return {"key": key, "title": title, "difficulty": difficulty, "est_hours": hours, "description": description,
            "features": features, "stretch": list(stretch)}


def unit(key: str, level: int, title: str, why: str, outcome: str, skills: List[str], steps: List[Dict],
         recap: List[str], build: Optional[Dict] = None, requires: Optional[str] = None) -> Dict:
    return {"key": key, "level": level, "title": title, "why": why, "outcome": outcome, "skills": skills,
            "steps": steps, "recap": recap, "build": build, "requires": requires}


def topic(name: str, goal: str, color: str, units: List[Dict]) -> Dict:
    return {"name": name, "goal": goal, "color": color, "units": units}


# ---------------------------------------------------------------- shared resources

PY_TUTORIAL = r("docs", "The Python tutorial (python.org)", "https://docs.python.org/3/tutorial/")
CS50P = r("course", "CS50's Introduction to Programming with Python (Harvard, free)", "https://cs50.harvard.edu/python/")
THINK_PY = r("book", "Think Python, 3rd edition (free online)", "https://allendowney.github.io/ThinkPython/")
EXERCISM_PY = r("practice", "Exercism: Python track", "https://exercism.org/tracks/python")
REAL_PY = r("article", "Real Python tutorials", "https://realpython.com/")
JS_INFO = r("book", "The Modern JavaScript Tutorial (javascript.info)", "https://javascript.info/")
MDN = r("docs", "MDN Web Docs", "https://developer.mozilla.org/en-US/docs/Learn")
TS_HANDBOOK = r("docs", "The TypeScript Handbook", "https://www.typescriptlang.org/docs/handbook/intro.html")
EXERCISM_JS = r("practice", "Exercism: JavaScript track", "https://exercism.org/tracks/javascript")
ODIN = r("course", "The Odin Project (free full-stack curriculum)", "https://www.theodinproject.com/")
REACT = r("docs", "react.dev: Learn React", "https://react.dev/learn")
NEXT = r("docs", "Next.js: Learn course", "https://nextjs.org/learn")
FASTAPI = r("docs", "FastAPI tutorial", "https://fastapi.tiangolo.com/tutorial/")
NODE = r("docs", "Node.js: Learn", "https://nodejs.org/en/learn")
EXPRESS = r("docs", "Express guide", "https://expressjs.com/en/guide/routing.html")
SQLBOLT = r("practice", "SQLBolt: interactive SQL lessons", "https://sqlbolt.com/")
PG_DOCS = r("docs", "PostgreSQL tutorial (official docs)", "https://www.postgresql.org/docs/current/tutorial.html")
USE_INDEX = r("book", "Use The Index, Luke (SQL indexing, free)", "https://use-the-index-luke.com/")
REDIS = r("docs", "Redis docs: data types", "https://redis.io/docs/latest/develop/data-types/")
NEETCODE = r("practice", "NeetCode roadmap (problems by pattern)", "https://neetcode.io/roadmap")
TIH = r("article", "Tech Interview Handbook", "https://www.techinterviewhandbook.org/")
SDP = r("book", "The System Design Primer (GitHub)", "https://github.com/donnemartin/system-design-primer")
BBG = r("video", "ByteByteGo: system design (YouTube)", "https://www.youtube.com/@ByteByteGo")
HELLO = r("course", "Hello Interview: System Design in a Hurry", "https://www.hellointerview.com/learn/system-design/in-a-hurry/introduction")
MISSING = r("course", "The Missing Semester of Your CS Education (MIT)", "https://missing.csail.mit.edu/")
GIT_BOOK = r("book", "Pro Git (free online)", "https://git-scm.com/book/en/v2")
DOCKER = r("docs", "Docker: Get started", "https://docs.docker.com/get-started/")
GH_ACTIONS = r("docs", "GitHub Actions: quickstart", "https://docs.github.com/en/actions/writing-workflows/quickstart")
AWS_SB = r("course", "AWS Skill Builder (free courses)", "https://skillbuilder.aws/")
TERRAFORM = r("docs", "Terraform tutorials", "https://developer.hashicorp.com/terraform/tutorials")
K8S = r("docs", "Kubernetes basics tutorial", "https://kubernetes.io/docs/tutorials/kubernetes-basics/")
KAGGLE = r("course", "Kaggle Learn (free micro-courses)", "https://www.kaggle.com/learn")
PANDAS = r("docs", "pandas: getting started", "https://pandas.pydata.org/docs/getting_started/index.html")
ISLP = r("book", "An Introduction to Statistical Learning, Python edition (free PDF)", "https://www.statlearning.com/")
SKLEARN = r("docs", "scikit-learn user guide", "https://scikit-learn.org/stable/user_guide.html")
STATQUEST = r("video", "StatQuest with Josh Starmer (YouTube)", "https://www.youtube.com/@statquest")
FASTAI = r("course", "Practical Deep Learning for Coders (fast.ai)", "https://course.fast.ai/")
PYTORCH = r("docs", "PyTorch: learn the basics", "https://pytorch.org/tutorials/beginner/basics/intro.html")
ANTHROPIC_COURSES = r("course", "Anthropic courses: API, prompting, tool use (GitHub)", "https://github.com/anthropics/courses")
ANTHROPIC_DOCS = r("docs", "Anthropic API docs", "https://docs.anthropic.com/")
DLAI = r("course", "DeepLearning.AI short courses (free)", "https://www.deeplearning.ai/short-courses/")
KARPATHY = r("video", "Andrej Karpathy: Intro to Large Language Models (YouTube)", "https://www.youtube.com/@AndrejKarpathy")
DART = r("docs", "Dart language tour", "https://dart.dev/language")
FLUTTER = r("docs", "Flutter: get started and codelabs", "https://docs.flutter.dev/get-started")

# ---------------------------------------------------------------- topics

TOPICS: Dict[str, Dict] = {}

TOPICS["python"] = topic(
    "Python", "Write clean, idiomatic Python and use its tooling with confidence.", "#3566d6", [
        unit("py-start", 1, "Python first steps",
             "Every other Python topic builds on variables, control flow and functions.",
             "Write small programs that read input, make decisions and loop.", ["Python"],
             [learn("Variables, types and control flow", 150, ["Work through CS50P lectures 0-1.", "Write a number-guessing game."],
                    "The game runs and you can explain every line.", [CS50P, PY_TUTORIAL]),
              learn("Functions and modules", 120, ["CS50P lecture 2 and 4.", "Split a script into two modules."],
                    "You can write and import your own functions.", [CS50P, THINK_PY]),
              practice("10 small exercises", 150, ["Solve 10 Exercism Python exercises."], "10 exercises submitted.", [EXERCISM_PY])],
             ["What's the difference between a function returning a value and printing it?",
              "When would you use a while loop instead of a for loop?"]),
        unit("py-data", 1, "Data structures, files and errors",
             "Real programs move data around: lists, dicts, files and things that go wrong.",
             "Pick the right container, read and write files, and handle errors cleanly.", ["Python"],
             [learn("Lists, dicts, sets and comprehensions", 150, ["Python tutorial chapter 5.", "Rewrite three loops as comprehensions."],
                    "You can say which container fits a job and why.", [PY_TUTORIAL]),
              learn("Files, JSON and exceptions", 120, ["CS50P lectures 3 and 6.", "Read a CSV, write JSON, handle a missing file."],
                    "Your script fails with a clear message instead of a traceback.", [CS50P])],
             ["Why is looking up a key in a dict fast?", "When should you catch an exception, and when let it crash?"],
             build=project("py-cli-tracker", "Command-line tracker", "beginner", 6,
                           "Track something you care about (expenses, books, workouts) from the terminal, saved to JSON.",
                           ["add, list, edit and delete entries", "totals or stats per category", "clear error messages", "data saved to a JSON file"],
                           ["export to CSV"]),
             requires=None),
        unit("py-idiomatic", 2, "Idiomatic Python and OOP",
             "Reviewers judge Python by how idiomatic it is.",
             "Use classes, dataclasses, generators and context managers where they fit.", ["Python"],
             [learn("Classes and dataclasses", 150, ["Real Python: object-oriented programming.", "Convert a dict-based model into dataclasses."],
                    "You can explain __init__, __repr__ and when a dataclass beats a dict.", [REAL_PY]),
              learn("Iterators, generators and decorators", 150, ["Real Python articles on generators and decorators.", "Write a @timer decorator."],
                    "You've written a generator and a decorator yourself.", [REAL_PY]),
              practice("Refactor your tracker", 120, ["Refactor your earlier project with what you learned."], "The code is shorter and clearer than before.")],
             ["What does a generator save compared to building a list?", "What problem does a context manager solve?"]),
        unit("py-tooling", 2, "Tooling and testing",
             "Professional Python means virtual environments, formatting, type hints and tests.",
             "Set up a project with uv, ruff and pytest, and write useful tests.", ["Python", "CI/CD"],
             [learn("Packaging and environments", 90, ["Create a project with uv and a pyproject.toml.", "Add ruff for linting and formatting."],
                    "A fresh clone installs and runs with one command.", [r("docs", "uv documentation", "https://docs.astral.sh/uv/")]),
              learn("Testing with pytest", 150, ["pytest getting started and fixtures.", "Write tests for your tracker, including edge cases."],
                    "Tests cover the main paths and one bug you found.", [r("docs", "pytest documentation", "https://docs.pytest.org/en/stable/getting-started.html")]),
              learn("Type hints", 90, ["Add type hints to your project and run mypy.", "Fix every error it reports."], "mypy passes.")],
             ["What makes a test useful rather than just green?", "What does a lock file protect you from?"],
             build=project("py-package", "Publishable Python package", "beginner", 6,
                           "Turn a small utility into a proper package with tests and CI.",
                           ["pyproject.toml managed with uv", "ruff, mypy and pytest passing", "GitHub Actions running tests on push", "a README with usage"])),
        unit("py-advanced", 3, "Async and performance",
             "Services and scrapers spend most of their time waiting; async and profiling fix that.",
             "Write async code with asyncio and find bottlenecks with a profiler.", ["Python"],
             [learn("asyncio", 150, ["Real Python: async IO in Python.", "Fetch 50 URLs concurrently with httpx."],
                    "The async version is clearly faster and you can say why.", [REAL_PY]),
              learn("Profiling", 90, ["Profile a slow script with cProfile.", "Fix the top hotspot."], "You measured before and after.")],
             ["When does async not help?", "Why measure before optimising?"]),
    ])

TOPICS["javascript"] = topic(
    "JavaScript & TypeScript", "Write modern JavaScript and type it with TypeScript.", "#c99a06", [
        unit("js-start", 1, "JavaScript fundamentals",
             "JavaScript runs every web page and many servers.",
             "Write programs with variables, functions, arrays and objects.", ["JavaScript"],
             [learn("Syntax, functions and control flow", 150, ["javascript.info part 1, chapters 1-2."], "You can solve small problems without looking up syntax.", [JS_INFO]),
              learn("Objects, arrays and their methods", 150, ["javascript.info chapters 4-5.", "Practise map, filter and reduce."], "You can transform data with array methods.", [JS_INFO]),
              practice("Exercises", 150, ["Solve 10 Exercism JavaScript exercises."], "10 exercises submitted.", [EXERCISM_JS])],
             ["What's the difference between let, const and var?", "What does reduce do, in your own words?"]),
        unit("js-async", 1, "The browser, the DOM and async code",
             "Interactive pages and API calls depend on the DOM, events and promises.",
             "Change a page with the DOM and fetch data with async/await.", ["JavaScript"],
             [learn("DOM and events", 150, ["MDN: manipulating documents and events.", "Build a to-do list in plain JS."], "The to-do list adds, completes and deletes items.", [MDN]),
              learn("Promises and async/await", 120, ["javascript.info: promises, async/await.", "Fetch data from a public API and render it."], "You can explain the event loop at a high level.", [JS_INFO])],
             ["What happens between calling fetch and getting data?", "Why can't you return a value from inside a callback?"],
             build=project("js-weather", "Weather dashboard", "beginner", 6, "A small page that shows the weather for a city from a free API.",
                           ["search by city", "loading and error states", "last searches saved in localStorage"])),
        unit("ts-core", 2, "TypeScript",
             "Most professional JavaScript is written in TypeScript now.",
             "Type functions, objects and API responses, and read compiler errors calmly.", ["TypeScript"],
             [learn("Types, interfaces and generics", 180, ["TypeScript Handbook: everyday types, narrowing, generics."], "You can type a function that works on any list.", [TS_HANDBOOK]),
              practice("Convert a project", 150, ["Convert your weather dashboard to TypeScript with strict mode."], "It builds with zero type errors.")],
             ["What's the difference between a type and an interface?", "What does narrowing mean?"]),
        unit("js-deep", 3, "JavaScript in depth",
             "Closures, modules and the event loop explain most bugs that look like magic.",
             "Explain closures, this, modules and the event loop, and use them deliberately.", ["JavaScript", "TypeScript"],
             [learn("Closures, this and prototypes", 150, ["javascript.info: closures, this, prototypes."], "You can predict the output of tricky snippets.", [JS_INFO]),
              learn("Modules and tooling", 90, ["ES modules, npm, and a bundler like Vite."], "You can set up a project from scratch.", [r("docs", "Vite guide", "https://vite.dev/guide/")])],
             ["What is a closure, and when have you used one?", "What does the bundler do for you?"]),
    ])

TOPICS["frontend"] = topic(
    "Frontend with React", "Build accessible, responsive interfaces with React.", "#7b56cf", [
        unit("fe-html-css", 1, "HTML and CSS",
             "Everything on the web ends up as HTML and CSS.",
             "Build a responsive, accessible page with semantic HTML and modern CSS.", [],
             [learn("Semantic HTML and accessibility", 120, ["MDN: HTML basics and accessibility."], "Your page works with a keyboard only.", [MDN]),
              learn("Flexbox, grid and responsive design", 150, ["MDN: CSS layout.", "Rebuild a page you like."], "It looks right on a phone and a laptop.", [MDN, ODIN])],
             ["Why use a button element instead of a clickable div?", "When would you pick grid over flexbox?"]),
        unit("fe-react", 2, "React fundamentals",
             "React is the most asked-for frontend library.",
             "Build components with props, state and effects.", ["React"],
             [learn("Components, props and state", 180, ["react.dev: Describing the UI and Adding interactivity."], "You've built a small app with several components.", [REACT]),
              learn("Effects and data fetching", 120, ["react.dev: Escape hatches (effects).", "Fetch and show data with loading and error states."], "You know when you don't need an effect.", [REACT])],
             ["What's the difference between props and state?", "What causes a component to re-render?"],
             build=project("fe-react-app", "React app on a public API", "intermediate", 10, "A multi-view React app on a free API (movies, books, recipes).",
                           ["search and filter", "a details view", "loading, empty and error states", "deployed and linked in the README"]),
             requires="js-async"),
        unit("fe-state", 2, "State, forms and routing",
             "Real apps have forms, shared state and several pages.",
             "Handle forms, share state and route between pages.", ["React", "TypeScript"],
             [learn("Forms and shared state", 150, ["react.dev: Managing state.", "Lift state up, then try context."], "You can explain why state lives where it does.", [REACT]),
              learn("Routing and testing", 150, ["Add a router.", "Test a component with Testing Library."], "Two components have tests.", [r("docs", "Testing Library docs", "https://testing-library.com/docs/react-testing-library/intro/")])],
             ["When is context the wrong tool?", "What should a component test check?"]),
        unit("fe-next", 3, "Next.js and performance",
             "Production React apps need server rendering, caching and fast loads.",
             "Build and deploy a Next.js app and measure its performance.", ["Next.js", "React"],
             [learn("Next.js App Router", 180, ["Next.js Learn course."], "You've finished the course app.", [NEXT]),
              learn("Web performance", 90, ["Measure Core Web Vitals with Lighthouse.", "Fix the biggest issue."], "Your score went up and you know why.", [r("article", "web.dev: Learn performance", "https://web.dev/learn/performance")])],
             ["What runs on the server and what in the browser?", "What slows down a first page load most?"],
             build=project("fe-next-app", "Full Next.js app", "advanced", 16, "A Next.js app with auth, a database and server rendering.",
                           ["sign in", "data stored in a database", "server-rendered pages", "deployed"])),
    ])

TOPICS["backend-python"] = topic(
    "Backend with Python", "Build and ship APIs with FastAPI and a real database.", "#1f7a5c", [
        unit("bp-http", 1, "HTTP and your first API",
             "Every backend speaks HTTP; knowing it well makes everything else easier.",
             "Explain requests, responses and status codes, and build a small FastAPI service.", ["Python", "FastAPI"],
             [learn("How HTTP works", 90, ["MDN: an overview of HTTP.", "Inspect requests in your browser's network tab."], "You can explain methods, headers and status codes.", [MDN]),
              learn("FastAPI basics", 180, ["FastAPI tutorial: first steps to request body."], "You have CRUD endpoints with validation.", [FASTAPI])],
             ["What's the difference between PUT and PATCH?", "When should an API return 404 vs 422?"],
             build=project("bp-url-shortener", "URL shortener API", "beginner", 8, "A small, complete REST API.",
                           ["create, look up and delete short links", "input validation", "click counts", "tests for every endpoint"]),
             requires="py-data"),
        unit("bp-data", 2, "Databases from Python",
             "Most backend work is reading and writing data safely.",
             "Use SQLAlchemy and migrations with Postgres.", ["Python", "PostgreSQL", "SQL"],
             [learn("SQLAlchemy and Alembic", 180, ["SQLAlchemy 2.0 tutorial (ORM part).", "Add Alembic migrations to your API."], "Schema changes go through migrations.", [r("docs", "SQLAlchemy 2.0 tutorial", "https://docs.sqlalchemy.org/en/20/tutorial/")]),
              practice("Move your API to Postgres", 120, ["Run Postgres in Docker and point your API at it."], "Your API stores data in Postgres.")],
             ["What is an N+1 query and how do you spot one?", "Why use migrations instead of editing tables by hand?"],
             requires="db-sql"),
        unit("bp-auth", 2, "Auth, testing and structure",
             "Real APIs have users, permissions and tests you trust.",
             "Add authentication, structure the code in layers and test it.", ["Python", "FastAPI"],
             [learn("Authentication", 150, ["FastAPI security tutorial.", "Hash passwords; never store them plainly."], "Users can sign up, log in and only see their data.", [FASTAPI]),
              learn("Testing APIs", 120, ["Test endpoints with TestClient and a test database."], "Tests run against a real database.", [FASTAPI])],
             ["Where should authorisation checks live?", "What's the risk of storing tokens in localStorage?"],
             build=project("bp-tasks-api", "Multi-user tasks API", "intermediate", 14, "A task manager API where every user sees only their own data.",
                           ["sign up and log in", "tasks per user with filters", "migrations", "tests and CI"])),
        unit("bp-prod", 3, "Production backend",
             "Shipping means background jobs, caching, logging and deploys.",
             "Deploy a service with background work, caching and useful logs.", ["Python", "Docker", "Redis"],
             [learn("Background jobs and caching", 150, ["Add a background task and a Redis cache to your API."], "A slow endpoint got fast and you can show the numbers.", [REDIS]),
              learn("Deploying and observing", 150, ["Containerise the API and deploy it.", "Add structured logs and a health check."], "It runs somewhere public with logs you can read.", [DOCKER])],
             ["When is a cache a bad idea?", "What do you log, and what never?"]),
    ])

TOPICS["backend-node"] = topic(
    "Backend with Node.js", "Build and ship APIs with Node.js, TypeScript and a real database.", "#3f8f2f", [
        unit("bn-node", 1, "Node.js and HTTP",
             "Node lets you use JavaScript on the server.",
             "Explain HTTP and build a small Express API.", ["Node.js", "Express"],
             [learn("How HTTP works", 90, ["MDN: an overview of HTTP."], "You can explain methods, headers and status codes.", [MDN]),
              learn("Node and Express", 180, ["Node.js Learn: getting started.", "Express guide: routing and middleware."], "You have CRUD endpoints with validation.", [NODE, EXPRESS])],
             ["What is middleware?", "When should an API return 404 vs 400?"],
             build=project("bn-notes-api", "Notes API", "beginner", 8, "A small REST API for notes.",
                           ["create, list, update and delete notes", "input validation", "error handling middleware", "tests"]),
             requires="js-async"),
        unit("bn-data", 2, "Databases and auth",
             "Real APIs store data and know who is calling.",
             "Use Postgres with an ORM, and add authentication.", ["Node.js", "PostgreSQL", "TypeScript"],
             [learn("Postgres with Prisma or Drizzle", 180, ["Pick one ORM and follow its getting-started guide."], "Your API stores data in Postgres with migrations.", [r("docs", "Prisma docs", "https://www.prisma.io/docs/getting-started")]),
              learn("Authentication", 150, ["Hash passwords; use httpOnly cookies for sessions."], "Users only see their own data.", [r("article", "OWASP cheat sheet: authentication", "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html")])],
             ["What does an ORM hide from you?", "Why httpOnly cookies?"],
             requires="db-sql"),
        unit("bn-prod", 3, "Structured services with NestJS",
             "Larger codebases need structure, tests and observability.",
             "Build a NestJS service with tests, logging and a deploy.", ["NestJS", "Node.js", "Docker"],
             [learn("NestJS", 180, ["NestJS docs: first steps to providers and modules."], "You understand modules, controllers and providers.", [r("docs", "NestJS documentation", "https://docs.nestjs.com/")]),
              learn("Deploy and observe", 120, ["Containerise and deploy it with logs and a health check."], "It runs publicly.", [DOCKER])],
             ["What does dependency injection buy you?", "What would you check first when a deploy fails?"],
             build=project("bn-shop-api", "Shop API", "intermediate", 16, "A small e-commerce API.",
                           ["products, cart and orders", "auth and roles", "migrations and tests", "deployed"])),
    ])

TOPICS["databases"] = topic(
    "Databases & SQL", "Query, design and tune relational databases.", "#13897c", [
        unit("db-sql", 1, "SQL fundamentals",
             "SQL is asked for in a huge share of engineering jobs.",
             "Write queries with joins, grouping and subqueries.", ["SQL"],
             [learn("SELECT, filtering and joins", 150, ["SQLBolt lessons 1-12."], "You can join three tables to answer a question.", [SQLBOLT]),
              learn("Grouping and subqueries", 120, ["SQLBolt lessons 13-18.", "PostgreSQL tutorial: advanced features."], "You can write a report query with GROUP BY.", [SQLBOLT, PG_DOCS]),
              practice("Practice queries", 120, ["Solve 15 SQL problems (LeetCode database set or similar)."], "15 problems solved.")],
             ["What's the difference between INNER and LEFT JOIN?", "When do you need HAVING?"]),
        unit("db-design", 2, "Schema design and transactions",
             "A good schema prevents whole classes of bugs.",
             "Design normalised schemas with constraints and use transactions correctly.", ["SQL", "PostgreSQL"],
             [learn("Modelling and constraints", 150, ["Design a schema for a library or shop: keys, foreign keys, checks."], "Bad data is rejected by the database, not just the app.", [PG_DOCS]),
              learn("Transactions and isolation", 120, ["Read about ACID and isolation levels.", "Reproduce a lost update and fix it."], "You can explain a race condition you caused.", [PG_DOCS])],
             ["When would you denormalise on purpose?", "What does a transaction guarantee?"]),
        unit("db-perf", 3, "Indexes and performance",
             "Slow queries are one of the most common production problems.",
             "Read query plans and add the right indexes.", ["PostgreSQL", "SQL"],
             [learn("Indexes", 150, ["Use The Index, Luke: chapters 1-3."], "You can explain why an index was or wasn't used.", [USE_INDEX]),
              learn("EXPLAIN ANALYZE", 120, ["Load a million rows and tune three slow queries."], "Each query is measurably faster.", [PG_DOCS])],
             ["Why can an index make writes slower?", "What does a sequential scan tell you?"]),
        unit("db-nosql", 3, "Redis and document stores",
             "Not every problem fits tables; caches and documents have their place.",
             "Use Redis for caching and know when a document store fits.", ["Redis", "MongoDB"],
             [learn("Redis", 120, ["Redis docs: data types.", "Cache an expensive query with a TTL."], "You can explain cache invalidation in your app.", [REDIS]),
              learn("Document databases", 90, ["MongoDB basics: documents and indexes."], "You can say when you'd choose it over Postgres.", [r("docs", "MongoDB manual: introduction", "https://www.mongodb.com/docs/manual/introduction/")])],
             ["What happens when the cache and database disagree?", "When is a document store a better fit?"]),
    ])

TOPICS["dsa"] = topic(
    "DSA & coding interviews", "Solve interview problems by recognising patterns.", "#d1386f", [
        unit("dsa-basics", 1, "Complexity, arrays and hashing",
             "Big-O and hash maps unlock most easy and medium problems.",
             "Analyse complexity and solve array and hashing problems.", [],
             [learn("Big-O", 90, ["Tech Interview Handbook: algorithms cheatsheet intro."], "You can state the complexity of your own code.", [TIH]),
              practice("Arrays and hashing", 240, ["NeetCode roadmap: arrays & hashing (easy and medium)."], "Each problem solved and explained out loud.", [NEETCODE])],
             ["Why is a hash map lookup O(1) on average?", "How do you trade memory for speed?"]),
        unit("dsa-patterns", 2, "Core patterns",
             "Two pointers, sliding window, stacks and binary search cover a large share of questions.",
             "Recognise and apply the core patterns under time pressure.", [],
             [practice("Two pointers and sliding window", 240, ["NeetCode roadmap: two pointers, sliding window."], "You can tell which pattern fits before coding.", [NEETCODE]),
              practice("Stacks and binary search", 240, ["NeetCode roadmap: stack, binary search."], "Mediums in under 30 minutes.", [NEETCODE])],
             ["What signals a sliding window problem?", "What's the invariant in binary search?"]),
        unit("dsa-trees", 2, "Trees, graphs and heaps",
             "Recursion and traversal questions show up in almost every loop.",
             "Traverse trees and graphs and use heaps.", [],
             [practice("Trees", 240, ["NeetCode roadmap: trees."], "You can write DFS and BFS from memory.", [NEETCODE]),
              practice("Graphs and heaps", 240, ["NeetCode roadmap: heap, graphs."], "You can model a problem as a graph.", [NEETCODE])],
             ["When BFS rather than DFS?", "What does a heap give you that a sorted list doesn't?"]),
        unit("dsa-dp", 3, "Dynamic programming and mocks",
             "DP is the hardest pattern for most people, and mocks build interview calm.",
             "Solve 1-D and 2-D DP problems and pass timed mock interviews.", [],
             [practice("Dynamic programming", 300, ["NeetCode roadmap: 1-D and 2-D DP."], "You can define the state and transition before coding.", [NEETCODE]),
              practice("Mock interviews", 180, ["Do three timed mocks with a friend or a free mock site."], "Three mocks done, notes written.", [TIH])],
             ["How do you find the subproblem?", "What do you say when you're stuck in an interview?"]),
    ])

TOPICS["system-design"] = topic(
    "System design", "Design systems at scale and explain the trade-offs.", "#4f6b8a", [
        unit("sd-basics", 2, "System design fundamentals",
             "Senior interviews and real architecture work start here.",
             "Explain scaling, caching, load balancing and consistency trade-offs.", ["Microservices"],
             [learn("Building blocks", 180, ["System Design Primer: index topics.", "ByteByteGo videos on caching and load balancing."], "You can draw a scalable web app and explain each box.", [SDP, BBG]),
              learn("A framework for interviews", 90, ["Hello Interview: System Design in a Hurry."], "You have a step-by-step approach.", [HELLO])],
             ["When would you add a cache, and what breaks?", "What does the CAP theorem actually limit?"]),
        unit("sd-cases", 3, "Case studies",
             "Practising real designs is how the ideas stick.",
             "Design common systems end to end and defend your choices.", ["Microservices", "Kafka"],
             [practice("Classic designs", 300, ["Design a URL shortener, a chat app and a news feed; time-box each to 45 minutes."], "Three designs written up with trade-offs.", [HELLO, SDP]),
              learn("Queues and events", 120, ["Learn when to use a message queue like Kafka or SQS."], "You can explain at-least-once delivery.", [BBG])],
             ["How do you handle a hot key?", "What changes when you need exactly-once processing?"]),
    ])

TOPICS["devops"] = topic(
    "DevOps & cloud", "Deploy, automate and run software in the cloud.", "#0f7ea8", [
        unit("ops-linux", 1, "Linux, shell and Git",
             "Every server and every team runs on the shell and Git.",
             "Work comfortably in a terminal and use Git with branches and pull requests.", [],
             [learn("The shell", 150, ["Missing Semester: lectures 1-3."], "You can find, filter and script your way around.", [MISSING]),
              learn("Git", 120, ["Pro Git chapters 1-3.", "Practise branching, rebasing and resolving a conflict."], "You've resolved a merge conflict yourself.", [GIT_BOOK])],
             ["What's the difference between merge and rebase?", "How do you find what's using a port?"]),
        unit("ops-docker", 2, "Containers and CI/CD",
             "Containers and automated pipelines are how modern code ships.",
             "Containerise an app and run tests and deploys from CI.", ["Docker", "CI/CD"],
             [learn("Docker", 150, ["Docker: get started.", "Write a multi-stage Dockerfile and a compose file."], "Your app and database run with one command.", [DOCKER]),
              learn("CI with GitHub Actions", 120, ["GitHub Actions quickstart.", "Run tests and build an image on every push."], "A failing test blocks the merge.", [GH_ACTIONS])],
             ["What's in an image versus a container?", "What should CI check before deploying?"],
             build=project("ops-pipeline", "Containerised app with CI", "intermediate", 8, "Take an existing app and give it a full pipeline.",
                           ["multi-stage Dockerfile", "docker compose for local dev", "CI running tests and building the image", "deploy on merge"])),
        unit("ops-aws", 2, "Cloud fundamentals (AWS)",
             "AWS is the most requested cloud in job postings.",
             "Use core AWS services: IAM, EC2, S3, RDS and a managed container service.", ["AWS"],
             [learn("Core services", 240, ["AWS Skill Builder: Cloud Practitioner Essentials."], "You can explain IAM roles, VPCs and S3 in your own words.", [AWS_SB]),
              practice("Deploy something", 150, ["Deploy a container to a managed service with a database."], "It runs on AWS and you know what it costs.")],
             ["What's the difference between a role and a user?", "How do you keep a cloud bill under control?"]),
        unit("ops-iac", 3, "Infrastructure as code and Kubernetes",
             "Clicking in a console doesn't scale; code and orchestration do.",
             "Define infrastructure in Terraform and run an app on Kubernetes.", ["Terraform / IaC", "Kubernetes"],
             [learn("Terraform", 180, ["Terraform tutorials: get started on AWS."], "You can create and destroy your stack from code.", [TERRAFORM]),
              learn("Kubernetes", 180, ["Kubernetes basics tutorial.", "Deploy your app to a local cluster."], "Your app runs with a deployment and a service.", [K8S])],
             ["What does Terraform state do?", "What problem does Kubernetes solve that Docker alone doesn't?"]),
    ])

TOPICS["data-ml"] = topic(
    "Data analysis & ML", "Analyse data and train machine learning models yourself.", "#a77d0b", [
        unit("ml-pandas", 1, "Data analysis with pandas",
             "Every ML project starts with understanding the data.",
             "Load, clean, explore and plot a dataset.", ["Pandas / NumPy", "Python"],
             [learn("pandas and NumPy", 180, ["Kaggle Learn: pandas.", "pandas getting started tutorials."], "You can answer questions about a dataset with code.", [KAGGLE, PANDAS]),
              practice("Explore a dataset", 150, ["Pick a Kaggle dataset; clean it and make 5 plots that say something."], "A notebook with findings.", [KAGGLE])],
             ["How do you handle missing values?", "What's the difference between a Series and a DataFrame?"],
             requires="py-data"),
        unit("ml-stats", 1, "Statistics for ML",
             "Models are statistics; without the basics, results are guesses.",
             "Use distributions, sampling and hypothesis tests correctly.", [],
             [learn("Core statistics", 180, ["StatQuest: statistics fundamentals playlist."], "You can explain p-values and confidence intervals plainly.", [STATQUEST])],
             ["What does a p-value not tell you?", "Why does sample size matter?"]),
        unit("ml-classic", 2, "Classic machine learning",
             "Most ML in production is still regression, trees and boosting.",
             "Train, evaluate and tune models with scikit-learn.", ["Python"],
             [learn("Supervised learning", 240, ["ISLP chapters 2-4.", "scikit-learn: linear models and trees."], "You can explain bias and variance.", [ISLP, SKLEARN]),
              practice("A Kaggle competition", 180, ["Enter a beginner Kaggle competition with a proper validation set."], "A submission and a write-up.", [KAGGLE])],
             ["Why hold out a test set?", "When does a simple model beat a complex one?"],
             build=project("ml-predictor", "End-to-end prediction project", "intermediate", 12, "Predict something real from a public dataset and explain it.",
                           ["cleaning and features", "a baseline and a better model", "proper evaluation", "a short report of what you learned"])),
        unit("ml-deep", 3, "Deep learning",
             "Neural networks power vision, language and modern AI.",
             "Train neural networks with PyTorch.", ["PyTorch"],
             [learn("Practical deep learning", 300, ["fast.ai lessons 1-4."], "You've trained an image classifier.", [FASTAI]),
              learn("PyTorch basics", 180, ["PyTorch: learn the basics."], "You can write a training loop yourself.", [PYTORCH])],
             ["What does a loss function do?", "How do you spot overfitting?"]),
    ])

TOPICS["ai-eng"] = topic(
    "AI engineering with LLMs", "Build reliable features on top of large language models.", "#c2551f", [
        unit("ai-llm", 1, "How LLMs work and calling them",
             "Good AI features start with a working model of what an LLM does.",
             "Explain tokens and context, and call an LLM API with streaming.", ["LLMs / GenAI"],
             [learn("What an LLM is", 120, ["Karpathy: Intro to Large Language Models."], "You can explain pre-training and why models hallucinate.", [KARPATHY]),
              learn("The API", 120, ["Anthropic API docs: messages and streaming.", "Build a small CLI chat."], "Your chat streams responses.", [ANTHROPIC_DOCS])],
             ["What is a token?", "Why do models make things up?"],
             requires="py-data"),
        unit("ai-prompts", 2, "Prompting, structured output and tools",
             "Reliable output and tool calls turn a chatbot into a product.",
             "Write robust prompts, get structured output and let the model call tools.", ["LLMs / GenAI", "AI agents"],
             [learn("Prompt engineering", 150, ["Anthropic courses: prompt engineering tutorial."], "You've made a flaky prompt reliable.", [ANTHROPIC_COURSES]),
              learn("Tool use", 150, ["Anthropic courses: tool use.", "Let a model call two of your functions."], "The model calls your tools correctly.", [ANTHROPIC_COURSES])],
             ["How do you make output parseable every time?", "What can go wrong when a model calls tools?"]),
        unit("ai-rag", 2, "Retrieval-augmented generation",
             "Most business AI features answer questions over private documents.",
             "Build RAG with embeddings and a vector store, and measure its quality.", ["RAG / vector DB", "LLMs / GenAI"],
             [learn("Embeddings and retrieval", 180, ["DeepLearning.AI short courses on RAG and embeddings."], "You can explain chunking and retrieval.", [DLAI]),
              practice("Evaluate it", 120, ["Write 20 test questions and measure answer quality."], "You have numbers, not vibes.")],
             ["Why does chunk size matter?", "How do you know the answer is grounded?"],
             build=project("ai-docs-qa", "Ask-your-docs app", "intermediate", 14, "Answer questions over a set of documents with sources.",
                           ["ingest and chunk documents", "retrieval with a vector store", "answers with citations", "an eval set with scores"])),
        unit("ai-agents", 3, "Agents and evals",
             "Agents chain many model calls; evals keep them honest.",
             "Build a multi-step agent and an evaluation suite for it.", ["AI agents", "LLMs / GenAI"],
             [learn("Agent patterns", 180, ["Anthropic: building effective agents.", "Build an agent that plans and uses tools."], "It completes a multi-step task.", [ANTHROPIC_DOCS]),
              learn("Evals", 120, ["Write automated evals for your agent."], "You can tell if a change made it better or worse.", [DLAI])],
             ["When is an agent the wrong design?", "What makes an eval trustworthy?"]),
    ])

TOPICS["mobile"] = topic(
    "Mobile with Flutter", "Build and ship cross-platform mobile apps.", "#0a6cc9", [
        unit("mob-dart", 1, "Dart fundamentals",
             "Flutter apps are written in Dart.",
             "Write Dart with classes, null safety and async code.", ["Dart"],
             [learn("The Dart language", 150, ["Dart language tour."], "You can write small Dart programs.", [DART])],
             ["What does null safety protect you from?", "What's a Future?"]),
        unit("mob-ui", 2, "Flutter UI",
             "Widgets and layout are most of Flutter work.",
             "Build multi-screen apps with layouts, navigation and forms.", ["Flutter", "Dart"],
             [learn("Widgets and layout", 180, ["Flutter: get started and the first codelab."], "You've built the codelab app.", [FLUTTER]),
              learn("Navigation and forms", 120, ["Add screens, navigation and a validated form."], "Your app has three screens.", [FLUTTER])],
             ["Stateless vs stateful widgets?", "How does Flutter decide what to rebuild?"],
             build=project("mob-app", "Mobile habit tracker", "intermediate", 12, "A habit tracker app with local storage.",
                           ["add and complete habits", "streaks", "data saved on device", "runs on a phone"]),
             requires="mob-dart"),
        unit("mob-ship", 3, "State, backends and release",
             "Real apps talk to servers and ship to stores.",
             "Manage state, call an API and prepare a store release.", ["Flutter", "Firebase"],
             [learn("State management and APIs", 180, ["Pick Riverpod or Bloc; connect to a REST API or Firebase."], "Data loads with loading and error states.", [FLUTTER]),
              learn("Releasing", 90, ["Flutter docs: build and release for Android or iOS."], "You have a signed release build.", [FLUTTER])],
             ["Where should state live?", "What can go wrong in a store review?"]),
    ])

# ---------------------------------------------------------------- goals

# Each goal suggests topics with a weight: 3 = main focus, 2 = supporting, 1 = a little each week.
GOALS: Dict[str, Dict] = {
    "backend-python": {"label": "Backend developer (Python)",
                       "topics": {"python": 3, "backend-python": 3, "databases": 2, "devops": 2, "dsa": 1, "system-design": 1}},
    "backend-node": {"label": "Backend developer (Node.js)",
                     "topics": {"javascript": 3, "backend-node": 3, "databases": 2, "devops": 2, "dsa": 1, "system-design": 1}},
    "frontend": {"label": "Frontend developer",
                 "topics": {"javascript": 3, "frontend": 3, "dsa": 1}},
    "fullstack": {"label": "Full-stack developer (TypeScript)",
                  "topics": {"javascript": 3, "frontend": 2, "backend-node": 2, "databases": 2, "devops": 1}},
    "ai": {"label": "AI engineer (apps on LLMs)",
           "topics": {"python": 3, "ai-eng": 3, "backend-python": 2, "databases": 1, "data-ml": 1}},
    "data-ml": {"label": "Data scientist / ML engineer",
                "topics": {"python": 2, "data-ml": 3, "databases": 2}},
    "devops": {"label": "DevOps / cloud engineer",
               "topics": {"devops": 3, "python": 2, "system-design": 1, "databases": 1}},
    "mobile": {"label": "Mobile developer (Flutter)",
               "topics": {"mobile": 3, "databases": 1, "dsa": 1}},
    "interviews": {"label": "Pass coding interviews",
                   "topics": {"dsa": 3, "system-design": 2, "python": 1}},
    "custom": {"label": "Something else (pick topics yourself)", "topics": {}},
}

EXPERIENCE = {
    "new": {"label": "New to programming", "min_level": 1, "time_factor": 1.25},
    "some": {"label": "I've written some code", "min_level": 1, "time_factor": 1.0},
    "experienced": {"label": "I work as a developer", "min_level": 2, "time_factor": 0.8},
}

DEPTH = {
    "essentials": {"label": "The essentials", "max_level": 2},
    "deep": {"label": "In depth, including advanced units", "max_level": 3},
}
