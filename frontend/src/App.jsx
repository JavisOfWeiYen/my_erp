import { Routes, Route } from 'react-router-dom'

import Layout from '@/components/Layout'
import ProtectedRoute from '@/components/ProtectedRoute'
import AccountsPayablePage from '@/pages/AccountsPayablePage'
import AccountsReceivablePage from '@/pages/AccountsReceivablePage'
import AgingPage from '@/pages/AgingPage'
import CategoriesPage from '@/pages/CategoriesPage'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import MenuManagementPage from '@/pages/MenuManagementPage'
import NotFoundPage from '@/pages/NotFoundPage'
import CustomersPage from '@/pages/CustomersPage'
import EmployeesPage from '@/pages/EmployeesPage'
import InventoryPage from '@/pages/InventoryPage'
import ProductsPage from '@/pages/ProductsPage'
import PurchasesPage from '@/pages/PurchasesPage'
import ReportsPage from '@/pages/ReportsPage'
import SalesPage from '@/pages/SalesPage'
import StockAdjustmentsPage from '@/pages/StockAdjustmentsPage'
import SuppliersPage from '@/pages/SuppliersPage'
import UsersPage from '@/pages/UsersPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="products" element={<ProductsPage />} />
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="suppliers" element={<SuppliersPage />} />
          <Route path="purchases" element={<PurchasesPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="sales" element={<SalesPage />} />
          <Route path="inventory" element={<InventoryPage />} />
          <Route path="adjustments" element={<StockAdjustmentsPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="accounts-receivable" element={<AccountsReceivablePage />} />
          <Route path="accounts-payable" element={<AccountsPayablePage />} />
          <Route path="aging" element={<AgingPage />} />
        </Route>

        <Route element={<ProtectedRoute roles={['admin']} />}>
          <Route element={<Layout />}>
            <Route path="users" element={<UsersPage />} />
            <Route path="employees" element={<EmployeesPage />} />
            <Route path="menu-management" element={<MenuManagementPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
