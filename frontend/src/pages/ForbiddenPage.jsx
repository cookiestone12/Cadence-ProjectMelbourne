import { Link } from "react-router-dom";

export default function ForbiddenPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center 
text-center px-6">
      <h1 className="text-6xl font-bold mb-4">403</h1>

      <h2 className="text-2xl font-semibold mb-2">
        Permission Denied
      </h2>

      <p className="mb-6">
        You do not have permission to access this page.
      </p>

      <Link
        to="/"
        className="px-6 py-3 rounded-lg bg-[#5B8A72] text-white"
      >
        Return Home
      </Link>
    </div>
  );
}
