# SDLC Agent Frontend

Modern Next.js 14 frontend for the SDLC Agent multi-agent system.

## Features

- **Dashboard** - Overview of system metrics, active workflows, and agent activity
- **Projects** - Manage software development projects
- **Workflows** - Real-time visualization of SDLC automation workflows
- **Activity Feed** - Live agent actions and decision tracking
- **Human-in-the-Loop** - Approve, review, and provide input to agents
- **Dark Mode** - Full light/dark theme support

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS + shadcn/ui
- **State Management**: Zustand
- **Data Fetching**: TanStack Query
- **Real-time**: Socket.IO
- **Animations**: Framer Motion
- **Charts**: Recharts

## Getting Started

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

Create a `.env.local` file:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=http://localhost:8000
```

## Project Structure

```
src/
├── app/                    # Next.js App Router pages
│   ├── layout.tsx         # Root layout with providers
│   ├── page.tsx           # Dashboard home page
│   └── globals.css        # Global styles + CSS variables
├── components/
│   ├── ui/                # shadcn/ui components
│   ├── dashboard.tsx      # Main dashboard layout
│   ├── providers.tsx      # React Query + Theme providers
│   ├── projects/          # Project management components
│   ├── workflows/         # Workflow visualization
│   ├── agents/            # Agent activity components
│   └── metrics/           # Dashboard metrics
├── lib/
│   ├── api.ts             # API client
│   ├── stores.ts          # Zustand stores
│   └── utils.ts           # Utility functions
└── hooks/
    ├── use-toast.ts       # Toast notifications
    └── use-websocket.ts   # Real-time WebSocket hook
```

## Component Library

Uses shadcn/ui components styled with Tailwind CSS:

- Button, Input, Badge, Avatar
- Progress, ScrollArea, Separator
- DropdownMenu, Toast
- Custom SDLC phase colors

## License

MIT
