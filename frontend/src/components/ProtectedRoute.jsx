import { Navigate } from 'react-router-dom';
import { isAuthenticated } from '../lib/api';

/**
 * Wraps a route that requires authentication.
 * Redirects to /login if no valid token is present.
 */
export default function ProtectedRoute({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
