# secrets/

Mounted read-only into the app container at `/srv/secrets`. Put the Snowflake service user's
private key here (for example `rsa_key.p8`, generated with the `/gen-keypair` skill) and point
`SNOWFLAKE_PRIVATE_KEY_FILE` in `.env` at `/srv/secrets/rsa_key.p8`.

Everything in this folder except this README is ignored by git and excluded from the image.
