import env from '#start/env'

interface TokenResponse {
  access_token: string
  token_type: string
}

export class TokenService {
  private cachedToken: string | null = null
  private tokenExpiry: number = 0

  async getWidgetToken(): Promise<string> {
    // Return cached token if still valid (with 5 min buffer)
    const now: number = Date.now()
    if (this.cachedToken && this.tokenExpiry > now + 5 * 60 * 1000) {
      return this.cachedToken
    }

    const backendUrl: string | undefined = env.get('BACKEND_URL')
    const apiKey: string | undefined = env.get('WIDGET_API_KEY')

    if (!backendUrl || !apiKey) {
      throw new Error('BACKEND_URL or WIDGET_API_KEY is not configured')
    }

    const response: Response = await fetch(`${backendUrl}/api/auth/token`, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey,
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to get token: ${response.status} ${response.statusText}`)
    }

    const data = (await response.json()) as TokenResponse
    this.cachedToken = data.access_token

    // Token expires in 24 hours, cache for 23 hours
    this.tokenExpiry = now + 23 * 60 * 60 * 1000

    return this.cachedToken
  }
}

export const tokenService = new TokenService()
