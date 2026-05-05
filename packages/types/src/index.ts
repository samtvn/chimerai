// Shared API response types between SvelteKit frontend and FastAPI backend

export interface ApiResponse<T> {
  data: T;
  message?: string;
}

export interface ApiError {
  detail: string;
  status: number;
}

// Add your shared domain types below as the project grows
// Example:
// export interface Agent { ... }
// export interface Task { ... }
