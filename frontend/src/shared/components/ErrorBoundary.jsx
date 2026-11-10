import { Component } from 'react'
import Button from './Button.jsx'

/**
 * Menangkap error render di subtree-nya, mencegah seluruh app blank putih.
 * HARUS class component -- React 18 belum punya hook equivalent untuk ini.
 * Dipasang di main.jsx, membungkus <App/>.
 */
export class ErrorBoundary extends Component {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    console.error('Unhandled frontend render error', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="max-w-xl mx-auto p-6 text-center flex flex-col items-center gap-4">
          <p className="text-tertiary font-bold text-headline-sm">Terjadi kesalahan yang tidak terduga.</p>
          <p className="text-on-surface-variant text-body-md">
            Coba muat ulang halaman. Kalau masih terjadi, data kamu tetap aman.
          </p>
          <Button variant="secondary" onClick={() => window.location.reload()}>
            Muat ulang halaman
          </Button>
        </div>
      )
    }
    return this.props.children
  }
}
