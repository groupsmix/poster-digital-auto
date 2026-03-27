import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import Navbar from "@/components/Navbar";
import DashboardPage from "@/pages/DashboardPage";
import NewProductPage from "@/pages/NewProductPage";
import ProductListPage from "@/pages/ProductListPage";
import ProductDetailPage from "@/pages/ProductDetailPage";
import AIStatusPage from "@/pages/AIStatusPage";
import SocialPostsPage from "@/pages/SocialPostsPage";
import CalendarPage from "@/pages/CalendarPage";

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-zinc-950 text-zinc-100">
        <Navbar />
        <main className="mx-auto max-w-7xl px-4 py-8">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/new" element={<NewProductPage />} />
            <Route path="/products" element={<ProductListPage />} />
            <Route path="/products/:id" element={<ProductDetailPage />} />
            <Route path="/ai-status" element={<AIStatusPage />} />
            <Route path="/social-posts" element={<SocialPostsPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
          </Routes>
        </main>
        <Toaster
          theme="dark"
          position="bottom-right"
          toastOptions={{
            style: {
              background: "#18181b",
              border: "1px solid #27272a",
              color: "#fafafa",
            },
          }}
        />
      </div>
    </BrowserRouter>
  );
}

export default App;
