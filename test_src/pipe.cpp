#include<unistd.h>
#include<fcntl.h>
#include<sys/wait.h>

#include<iostream>
#include<string>
#include<thread>
#include<chrono>

int main(int argc, char **argv){
	if(argc < 2){
		std::cerr<<"insufficient arguments"<<std::endl;
		return 1;
	}
	std::cout<<argv[1]<<std::endl;

	int in[2], out[2];
	if(pipe(in) == -1){
		std::cerr<<"pipe(in) returned -1"<<std::endl;
		return 1;
	}
	if(pipe(out) == -1){
		std::cerr<<"pipe(out) returned -1"<<std::endl;
		return 1;
	}

	pid_t p = fork();

	switch(p){
	case -1:
		std::cerr<<"fork() returned -1"<<std::endl;
		return 1;
	case 0:{ // child
		close(in[1]);
		close(out[0]);
		dup2(in[0], STDIN_FILENO);
		dup2(out[1], STDOUT_FILENO);

		execvpe("gdb", (char *const[]){"gdb", argv[1], nullptr}, nullptr);
		perror("exec");
		exit(1);
	}
	default:{ // parent
		close(in[0]);
		close(out[1]);

		fcntl(out[0], F_SETFL, fcntl(out[0], F_GETFL, 0) | O_NONBLOCK);
		write(in[1], "set prompt \n", 12);

		volatile bool running = true;

		std::thread thrd([&](){
			std::string s;
			while(std::getline(std::cin, s)){
				s += '\n';

				write(in[1], s.data(), s.size());
				write(in[1], "p/x $rsp\n", 9);
				write(in[1], "p/x $rbp\n", 9);
				write(in[1], "p/x $rip\n", 9);
			}

			running = false;
		});

		for(; running; std::this_thread::sleep_for(std::chrono::milliseconds(1))){
			char buf[1<<12];
			ssize_t n;
			for(bool f=true; f; ){
				switch(n = read(out[0], buf, sizeof(buf))){
				case -1:
					if(errno == EAGAIN || errno == EWOULDBLOCK){
						f=false;
						break;
					}
					else{
						perror("read() err");
						goto term;
					}
				case 0:{
					goto term;
				}
				default:
					std::cout.write(buf, n);
				}
			}
		}

		thrd.join();

	term:
		std::cout<<"terminating"<<std::endl;

		kill(0, 9);
		waitpid(p, nullptr, 0);
	}
	}
}
