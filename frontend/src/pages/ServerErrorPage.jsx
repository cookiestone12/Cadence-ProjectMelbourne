import { Link } from "react-router-dom";

export default function ServerErrorPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center 
text-center px-6">
      <h1 className="text-6xl font-bold mb-4">500</h1>

      <h2 className="text-2xl font-semibold mb-2">
        Server Error
      </h2>

      <p className="mb-6">
        Something went wrong on our end. Please try again later.
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
