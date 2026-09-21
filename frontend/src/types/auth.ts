export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: string[];
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  full_name: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface AuthResponse {
  success: boolean;
  data?: {
    user: User;
    message?: string;
  };
  error?: {
    code: string;
    message: string;
  };
}
