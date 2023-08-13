install:
	NODE_OPTIONS=--openssl-legacy-provider npm run build
	rsync -avvz --delete-after dist/ trezor:/home/www/zpevnik.jmq.cz

debug:
	NODE_OPTIONS=--openssl-legacy-provider npm run serve
