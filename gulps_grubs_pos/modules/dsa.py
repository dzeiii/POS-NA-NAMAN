class CartNode:
    def __init__(self, product_id, name, price, quantity):
        self.product_id, self.name, self.price, self.quantity = product_id, name, price, quantity
        self.next = None

class LinkedListCart:
    """Singly linked list: add, remove, traverse, and total the cashier cart."""
    def __init__(self): self.head = None
    def add(self, product_id, name, price, quantity):
        cur = self.head
        while cur:
            if cur.product_id == product_id:
                cur.quantity += quantity
                return
            cur = cur.next
        node = CartNode(product_id, name, price, quantity)
        node.next = self.head
        self.head = node
    def remove(self, product_id):
        prev, cur = None, self.head
        while cur:
            if cur.product_id == product_id:
                if prev: prev.next = cur.next
                else: self.head = cur.next
                return
            prev, cur = cur, cur.next
    def to_list(self):
        out, cur = [], self.head
        while cur:
            out.append({"product_id":cur.product_id,"name":cur.name,"price":cur.price,
                        "quantity":cur.quantity,"subtotal":cur.price*cur.quantity})
            cur = cur.next
        return out
    def total(self): return sum(x["subtotal"] for x in self.to_list())
    def clear(self): self.head = None

class AVLNode:
    def __init__(self, key, value):
        self.key, self.value, self.left, self.right, self.height = key, value, None, None, 1

class AVLTree:
    """AVL self-balancing binary search tree keyed by normalized product name."""
    def __init__(self): self.root = None
    def height(self, n): return n.height if n else 0
    def balance(self, n): return self.height(n.left)-self.height(n.right) if n else 0
    def rotate_right(self, y):
        x, t = y.left, y.left.right
        x.right, y.left = y, t
        y.height = 1+max(self.height(y.left),self.height(y.right))
        x.height = 1+max(self.height(x.left),self.height(x.right))
        return x
    def rotate_left(self, x):
        y, t = x.right, x.right.left
        y.left, x.right = x, t
        x.height = 1+max(self.height(x.left),self.height(x.right))
        y.height = 1+max(self.height(y.left),self.height(y.right))
        return y
    def insert(self, key, value):
        def _insert(n):
            if not n: return AVLNode(key,value)
            if key < n.key: n.left = _insert(n.left)
            elif key > n.key: n.right = _insert(n.right)
            else: n.value = value; return n
            n.height = 1+max(self.height(n.left),self.height(n.right))
            b = self.balance(n)
            if b > 1 and key < n.left.key: return self.rotate_right(n)
            if b < -1 and key > n.right.key: return self.rotate_left(n)
            if b > 1 and key > n.left.key:
                n.left = self.rotate_left(n.left); return self.rotate_right(n)
            if b < -1 and key < n.right.key:
                n.right = self.rotate_right(n.right); return self.rotate_left(n)
            return n
        self.root = _insert(self.root)
    def search_prefix(self, prefix):
        found = []
        def walk(n):
            if not n: return
            walk(n.left)
            if n.key.startswith(prefix): found.append(n.value)
            walk(n.right)
        walk(self.root)
        return found

class MinHeap:
    """Min-heap of (priority rank, timestamp, payload). Lower rank is served first."""
    def __init__(self): self.data = []
    def __len__(self): return len(self.data)
    def push(self, priority, timestamp, payload):
        self.data.append((priority,timestamp,payload)); i=len(self.data)-1
        while i:
            p=(i-1)//2
            if self.data[p][:2] <= self.data[i][:2]: break
            self.data[p],self.data[i]=self.data[i],self.data[p]; i=p
    def pop(self):
        if not self.data: raise IndexError("empty heap")
        self.data[0],self.data[-1]=self.data[-1],self.data[0]
        item=self.data.pop()
        i=0
        while True:
            l,r=2*i+1,2*i+2
            smallest=i
            if l<len(self.data) and self.data[l][:2]<self.data[smallest][:2]: smallest=l
            if r<len(self.data) and self.data[r][:2]<self.data[smallest][:2]: smallest=r
            if smallest==i: break
            self.data[i],self.data[smallest]=self.data[smallest],self.data[i]; i=smallest
        return item
