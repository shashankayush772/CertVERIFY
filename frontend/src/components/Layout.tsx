import { ReactNode } from "react";
import Navbar from "./Navbar";

const Layout = ({ children }: { children: ReactNode }) => (
  <div className="min-h-screen">
    <Navbar />
    <main className="pt-16">{children}</main>
  </div>
);

export default Layout;
