# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|

  config.vm.box = "ubuntu/xenial64"

  config.vm.synced_folder "./", "/project"

  script = <<-EOF
    export ANTLR4="/usr/local/lib/antlr-4.7-complete.jar"
    export CLASSPATH=".:$ANTLR4:$CLASSPATH"
    java -Xmx500M org.antlr.v4.Tool \$@
  EOF

  config.vm.provision "shell", inline: <<-SHELL
    sudo apt-get update
    sudo apt-get install -y build-essential default-jdk python3.5-dev python-pip maven
    #
    cd /usr/local/lib
    sudo curl -O http://www.antlr.org/download/antlr-4.7-complete.jar

    mkdir -p tmp_scripts && cd tmp_scripts
    echo '#{script}' > antlr4
    echo "java org.antlr.v4.runtime.misc.TestRig \$@" > grun
    sudo chmod 777 antlr4 grun
    sudo mv antlr4 grun /usr/local/bin
  SHELL
end

