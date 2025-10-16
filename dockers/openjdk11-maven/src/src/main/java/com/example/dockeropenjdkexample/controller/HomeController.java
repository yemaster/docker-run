package com.example.dockeropenjdkexample.controller;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class HomeController {

    // 从配置中获取OpenJDK版本
    @Value("${openjdk.version}")
    private String openjdkVersion;

    // 处理根路径请求，返回index.html页面
    @GetMapping("/")
    public String home(Model model) {
        // 将OpenJDK版本传递给前端页面
        model.addAttribute("openjdk_version", openjdkVersion);
        return "index";
    }
}
