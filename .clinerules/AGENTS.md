### Code structure

project-name/
├── services/                  # Whole application
│   ├── postgres               # dockerfile, settings and code for postgres
│   ├── redis/                 # dockerfile, settings and code for redis
│   └── frontend/              # dockerfile, settings and code for frontent
│   ...
├── justfile                   # justfile with commands
└── docker-compose.yaml        # Docker compose

### Overall architecture

Use two part architecture:

### frontent
Typescript + Next.js frontent and backend for frontent

### backend
Python based backend with all services separated by API routes

### Python code requirements

- each module has to have file level docstring
- each cladd has to have docstring
- each function has to have docstring