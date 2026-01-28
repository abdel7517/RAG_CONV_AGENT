import React from 'react'
import { ShoppingCart, Star, Truck, RotateCcw, Shield, Headphones, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'

const products = [
  { id: 1, name: 'Casque Audio Premium', price: 149.99, originalPrice: 199.99, rating: 4.5, reviews: 128, badge: 'Promo' },
  { id: 2, name: 'Montre Connectee', price: 299.99, rating: 4.8, reviews: 256, badge: 'Nouveau' },
  { id: 3, name: 'Enceinte Bluetooth', price: 79.99, originalPrice: 99.99, rating: 4.3, reviews: 89, badge: 'Promo' },
  { id: 4, name: 'Clavier Mecanique RGB', price: 129.99, rating: 4.7, reviews: 312 },
  { id: 5, name: 'Souris Gaming Pro', price: 69.99, rating: 4.6, reviews: 178 },
  { id: 6, name: 'Webcam 4K', price: 189.99, originalPrice: 229.99, rating: 4.4, reviews: 67, badge: 'Promo' },
]

function StarRating({ rating }) {
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          className={`h-4 w-4 ${star <= rating ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`}
        />
      ))}
    </div>
  )
}

function ProductCard({ product }) {
  return (
    <Card className="group overflow-hidden transition-all hover:shadow-lg">
      <div className="relative aspect-square bg-gradient-to-br from-slate-100 to-slate-200 flex items-center justify-center">
        <div className="text-6xl text-slate-400">
          <ShoppingCart className="h-16 w-16" />
        </div>
        {product.badge && (
          <Badge className="absolute top-3 left-3" variant={product.badge === 'Promo' ? 'destructive' : 'default'}>
            {product.badge}
          </Badge>
        )}
      </div>
      <CardContent className="p-4">
        <h3 className="font-semibold text-lg mb-2 group-hover:text-primary transition-colors">
          {product.name}
        </h3>
        <div className="flex items-center gap-2 mb-2">
          <StarRating rating={product.rating} />
          <span className="text-sm text-muted-foreground">({product.reviews})</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold text-primary">{product.price.toFixed(2)} EUR</span>
          {product.originalPrice && (
            <span className="text-sm text-muted-foreground line-through">{product.originalPrice.toFixed(2)} EUR</span>
          )}
        </div>
      </CardContent>
      <CardFooter className="p-4 pt-0">
        <Button className="w-full">
          <ShoppingCart className="h-4 w-4 mr-2" />
          Ajouter au panier
        </Button>
      </CardFooter>
    </Card>
  )
}

export function DemoEcommerceWebsite() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4">
          <div className="flex h-16 items-center justify-between">
            <div className="flex items-center gap-8">
              <a href="/" className="text-2xl font-bold text-primary">
                TechShop
              </a>
              <nav className="hidden md:flex items-center gap-6">
                <a href="#" className="text-sm font-medium hover:text-primary transition-colors">Accueil</a>
                <a href="#produits" className="text-sm font-medium hover:text-primary transition-colors">Produits</a>
                <a href="#" className="text-sm font-medium hover:text-primary transition-colors">Categories</a>
                <a href="#" className="text-sm font-medium hover:text-primary transition-colors">Contact</a>
              </nav>
            </div>
            <div className="flex items-center gap-4">
              <Button variant="ghost" size="icon" className="relative">
                <ShoppingCart className="h-5 w-5" />
                <Badge className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs">
                  3
                </Badge>
              </Button>
              <Button variant="outline" size="sm">
                <User className="h-4 w-4 mr-2" />
                Connexion
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-primary/10 via-background to-background py-20 md:py-32">
        <div className="container mx-auto px-4">
          <div className="max-w-3xl">
            <Badge className="mb-4" variant="secondary">Nouveautes 2025</Badge>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
              La tech a portee de main
            </h1>
            <p className="text-xl text-muted-foreground mb-8 max-w-2xl">
              Decouvrez notre selection de produits high-tech au meilleur prix.
              Livraison gratuite des 50EUR d'achat.
            </p>
            <div className="flex flex-wrap gap-4">
              <Button size="lg">
                Decouvrir nos produits
              </Button>
              <Button size="lg" variant="outline">
                Voir les promos
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Products Section */}
      <section id="produits" className="py-16 md:py-24">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">Nos produits populaires</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Une selection de nos meilleurs produits, choisis par nos clients
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
          <div className="text-center mt-12">
            <Button variant="outline" size="lg">
              Voir tous les produits
            </Button>
          </div>
        </div>
      </section>

      <Separator />

      {/* Features Section */}
      <section className="py-16 md:py-24 bg-muted/50">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
            <div className="flex flex-col items-center text-center p-6">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Truck className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">Livraison gratuite</h3>
              <p className="text-sm text-muted-foreground">Des 50EUR d'achat en France metropolitaine</p>
            </div>
            <div className="flex flex-col items-center text-center p-6">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <RotateCcw className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">Retours faciles</h3>
              <p className="text-sm text-muted-foreground">30 jours pour changer d'avis</p>
            </div>
            <div className="flex flex-col items-center text-center p-6">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Shield className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">Paiement securise</h3>
              <p className="text-sm text-muted-foreground">Vos donnees sont protegees</p>
            </div>
            <div className="flex flex-col items-center text-center p-6">
              <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Headphones className="h-6 w-6 text-primary" />
              </div>
              <h3 className="font-semibold mb-2">Support 24/7</h3>
              <p className="text-sm text-muted-foreground">Notre assistant IA est la pour vous aider</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div>
              <h3 className="text-lg font-bold mb-4">TechShop</h3>
              <p className="text-sm text-muted-foreground">
                Votre destination pour les meilleurs produits tech au meilleur prix.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Liens utiles</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-primary transition-colors">A propos</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">FAQ</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Livraison</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Retours</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Categories</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-primary transition-colors">Audio</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Montres</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Gaming</a></li>
                <li><a href="#" className="hover:text-primary transition-colors">Accessoires</a></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Contact</h4>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li>contact@techshop.fr</li>
                <li>01 23 45 67 89</li>
                <li>Paris, France</li>
              </ul>
            </div>
          </div>
          <Separator className="my-8" />
          <div className="text-center text-sm text-muted-foreground">
            <p>2025 TechShop. Tous droits reserves.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default DemoEcommerceWebsite
