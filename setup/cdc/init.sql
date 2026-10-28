-- Schema rút gọn để thấy CDC; amount_cents là số nguyên, 100 cents = 1 BRL.
CREATE TABLE public.orders (
    order_id VARCHAR(32) PRIMARY KEY,
    status TEXT NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0)
);
INSERT INTO public.orders VALUES ('o1', 'created', 15000), ('o2', 'created', 2500);
