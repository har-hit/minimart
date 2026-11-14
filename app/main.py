from pathlib import Path
from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
from .database import Base, engine, get_db
from .models import Product, Order, OrderItem

BASE_DIR = Path(__file__).resolve().parent
Base.metadata.create_all(bind=engine)

app = FastAPI(title="MiniMart", version="1.0.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

def seed_products(db: Session):
    if db.scalar(select(Product.id).limit(1)) is None:
        db.add_all([
            Product(name="Wireless Headphones", description="Comfortable headphones for everyday listening.", price=1499, stock=15, image_url="https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?w=700"),
            Product(name="Smart Watch", description="A simple smartwatch for your daily routine.", price=2299, stock=10, image_url="https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=700"),
            Product(name="Backpack", description="A durable backpack for work and travel.", price=999, stock=20, image_url="https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=700"),
            Product(name="Desk Lamp", description="Minimal desk lamp for your study setup.", price=799, stock=12, image_url="https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=700"),
        ])
        db.commit()

@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", db: Session = Depends(get_db)):
    seed_products(db)
    stmt = select(Product)
    if q.strip():
        stmt = stmt.where(Product.name.ilike(f"%{q.strip()}%"))
    products = db.scalars(stmt.order_by(Product.id.desc())).all()
    return templates.TemplateResponse("index.html", {"request": request, "products": products, "q": q})

@app.get("/products/{product_id}", response_class=HTMLResponse)
def product_detail(product_id: int, request: Request, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return templates.TemplateResponse("product.html", {"request": request, "product": product})

@app.post("/cart/add/{product_id}")
def add_to_cart(product_id: int, request: Request, quantity: int = Form(1), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or quantity < 1:
        raise HTTPException(status_code=400, detail="Invalid product or quantity")
    if product.stock < quantity:
        raise HTTPException(status_code=400, detail="Not enough stock")
    cart = {}
    for part in request.cookies.get("cart", "").split(","):
        if ":" in part:
            key, value = part.split(":")
            if key.isdigit() and value.isdigit():
                cart[int(key)] = int(value)
    cart[product_id] = min(cart.get(product_id, 0) + quantity, product.stock)
    response = RedirectResponse("/cart", status_code=303)
    response.set_cookie("cart", ",".join(f"{k}:{v}" for k, v in cart.items()), httponly=True, samesite="lax")
    return response

def read_cart(request: Request, db: Session):
    cart = {}
    for part in request.cookies.get("cart", "").split(","):
        if ":" in part:
            key, value = part.split(":")
            if key.isdigit() and value.isdigit():
                cart[int(key)] = int(value)
    rows, total = [], 0.0
    for product_id, quantity in cart.items():
        product = db.get(Product, product_id)
        if product:
            quantity = min(quantity, product.stock)
            subtotal = product.price * quantity
            rows.append({"product": product, "quantity": quantity, "subtotal": subtotal})
            total += subtotal
    return rows, total

@app.get("/cart", response_class=HTMLResponse)
def view_cart(request: Request, db: Session = Depends(get_db)):
    rows, total = read_cart(request, db)
    return templates.TemplateResponse("cart.html", {"request": request, "rows": rows, "total": total})

@app.post("/cart/remove/{product_id}")
def remove_from_cart(product_id: int, request: Request):
    cart = {}
    for part in request.cookies.get("cart", "").split(","):
        if ":" in part:
            key, value = part.split(":")
            if key.isdigit() and value.isdigit() and int(key) != product_id:
                cart[int(key)] = int(value)
    response = RedirectResponse("/cart", status_code=303)
    response.set_cookie("cart", ",".join(f"{k}:{v}" for k, v in cart.items()), httponly=True, samesite="lax")
    return response

@app.get("/checkout", response_class=HTMLResponse)
def checkout_page(request: Request, db: Session = Depends(get_db)):
    rows, total = read_cart(request, db)
    if not rows:
        return RedirectResponse("/cart", status_code=303)
    return templates.TemplateResponse("checkout.html", {"request": request, "rows": rows, "total": total})

@app.post("/checkout")
def checkout(request: Request, customer_name: str = Form(...), email: str = Form(...), address: str = Form(...), db: Session = Depends(get_db)):
    rows, total = read_cart(request, db)
    if not rows:
        raise HTTPException(status_code=400, detail="Your cart is empty")
    for row in rows:
        if row["quantity"] > row["product"].stock:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {row['product'].name}")
    order = Order(customer_name=customer_name, email=email, address=address, total=total)
    db.add(order)
    db.flush()
    for row in rows:
        product = row["product"]
        product.stock -= row["quantity"]
        order.items.append(OrderItem(product_id=product.id, product_name=product.name, quantity=row["quantity"], unit_price=product.price))
    db.commit()
    response = RedirectResponse(f"/orders/{order.id}", status_code=303)
    response.delete_cookie("cart")
    return response

@app.get("/orders/{order_id}", response_class=HTMLResponse)
def order_confirmation(order_id: int, request: Request, db: Session = Depends(get_db)):
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return templates.TemplateResponse("order.html", {"request": request, "order": order})

# Learning CRUD endpoints. Add authentication and authorization before production use.
@app.post("/admin/products")
def create_product(name: str = Form(...), description: str = Form(""), price: float = Form(...), stock: int = Form(0), db: Session = Depends(get_db)):
    if price < 0 or stock < 0:
        raise HTTPException(status_code=400, detail="Price and stock must be non-negative")
    product = Product(name=name, description=description, price=price, stock=stock)
    db.add(product)
    db.commit()
    return {"message": "Product created", "product_id": product.id}

@app.put("/api/products/{product_id}")
def update_product(product_id: int, name: str, price: float, stock: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if price < 0 or stock < 0:
        raise HTTPException(status_code=400, detail="Price and stock must be non-negative")
    product.name, product.price, product.stock = name, price, stock
    db.commit()
    return {"message": "Product updated"}

@app.delete("/api/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return {"message": "Product deleted"}
