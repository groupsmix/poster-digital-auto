import { Link, useLocation } from "react-router-dom";
import { LayoutDashboard, PlusCircle, Package, Cpu, Share2, BarChart3, Calendar, Sparkles, TrendingUp } from "lucide-react";

const links = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/new", label: "New Product", icon: PlusCircle },
  { to: "/products", label: "Products", icon: Package },
  { to: "/niches", label: "Niches", icon: Sparkles },
  { to: "/trends", label: "Trends", icon: TrendingUp },
  { to: "/social-posts", label: "Social Posts", icon: Share2 },
  { to: "/analytics", label: "Analytics", icon: BarChart3 },
  { to: "/calendar", label: "Calendar", icon: Calendar },
  { to: "/ai-status", label: "AI Status", icon: Cpu },
];

export default function Navbar() {
  const { pathname } = useLocation();

  return (
    <header className="sticky top-0 z-50 border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
        <Link to="/" className="mr-4 flex items-center gap-2">
          <span className="text-lg font-bold bg-gradient-to-r from-violet-400 via-fuchsia-400 to-pink-400 bg-clip-text text-transparent">
            AI Product Factory
          </span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map(({ to, label, icon: Icon }) => {
            const active = pathname === to || (to !== "/" && pathname.startsWith(to));
            return (
              <Link
                key={to}
                to={to}
                className={`flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                  active
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>

        {/* Mobile nav */}
        <nav className="flex items-center gap-1 md:hidden ml-auto">
          {links.map(({ to, icon: Icon }) => {
            const active = pathname === to || (to !== "/" && pathname.startsWith(to));
            return (
              <Link
                key={to}
                to={to}
                className={`rounded-md p-2 transition-colors ${
                  active
                    ? "bg-zinc-800 text-white"
                    : "text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200"
                }`}
              >
                <Icon className="h-5 w-5" />
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
