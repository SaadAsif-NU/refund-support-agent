import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CustomerApp from "./components/customer/CustomerApp";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CustomerApp />
  </StrictMode>,
);
