# 1. Clone and build
git clone https://github.com/hackerhouse-opensource/cve-2018-10933
cd cve-2018-10933
docker build -t cve-2018-10933 .

# 2. Verify it works
docker run -d --name cve-test -p 2222:22 cve-2018-10933
ssh -l myuser -p 2222 localhost   # should connect with password: mypassword

# 3. Save to tar
docker save -o cve-2018-10933.tar cve-2018-10933

# (optional) compress
docker save cve-2018-10933 | gzip > cve-2018-10933.tar.gz   