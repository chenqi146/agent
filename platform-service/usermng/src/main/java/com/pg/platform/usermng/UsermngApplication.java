package com.pg.platform.usermng;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;

@SpringBootApplication
@EnableDiscoveryClient
public class UsermngApplication {

	public static void main(String[] args) {
		SpringApplication.run(UsermngApplication.class, args);
	}

}
