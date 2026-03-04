### Subfinder
find all subdomains

    subfinder -d {domain} -all > {domain}_subdomains.txt

### dnsx
check services that are up using the subfinder output
    
    dnsx -l {subfinder_output.txt} > subs_alive.txt

### naabu
check ports on the active services

    naabu -l {dnsx_output.txt} top ports 1000

### httpx
check ports on the active services
does it answer http/https or not

    httpx -l {dnsx_output.txt} -ports 8080,80,443

### katana
crawler - goes to every link in the website

    katana -list {httpx_output.txt} -depth {number}

### nuclei
auto attacks

    nuclei -l {katana_outputs.txt} -severity medium,high,critical

