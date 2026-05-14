import { useCallback, useEffect, useMemo, useState } from 'react'

import * as authApi from '@/api/auth'

import { AuthContext } from './AuthContext'

const TOKEN_KEY = 'access_token'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(token))

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!token) {
        if (!cancelled) {
          setUser(null)
          setLoading(false)
        }
        return
      }
      setLoading(true)
      try {
        const u = await authApi.getCurrentUser()
        if (!cancelled) setUser(u)
      } catch {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY)
          setToken(null)
          setUser(null)
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [token])

  const login = useCallback(async (username, password) => {
    const { access_token: accessToken } = await authApi.login(username, password)
    localStorage.setItem(TOKEN_KEY, accessToken)
    setToken(accessToken)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const hasRole = useCallback(
    (...roles) => Boolean(user && roles.includes(user.role?.name)),
    [user],
  )

  const value = useMemo(
    () => ({
      token,
      user,
      loading,
      isAuthenticated: Boolean(token && user),
      login,
      logout,
      hasRole,
    }),
    [token, user, loading, login, logout, hasRole],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
