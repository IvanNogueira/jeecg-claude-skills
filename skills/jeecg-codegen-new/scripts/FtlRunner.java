import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONReader;
import freemarker.core.TemplateClassResolver;
import freemarker.template.Configuration;
import freemarker.template.Template;
import freemarker.template.TemplateExceptionHandler;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.StringWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.stream.Collectors;

public class FtlRunner {

    private static final Pattern VAR_RE = Pattern.compile("\\$\\{([a-zA-Z_][a-zA-Z0-9_]*)\\}");
    private static final Pattern SUB_RE = Pattern.compile("\\[1-n\\]");
    private static final String SEGMENT_PREFIX = "#segment#";

    public static void main(String[] args) throws Exception {
        if (args.length < 4) {
            System.err.println("Usage: FtlRunner <templateRoot> <stylePath> <ctxJson> <outputDir>");
            System.err.println("  stylePath e.g. default/one  (relative to templateRoot)");
            System.exit(2);
        }
        Path templateRoot = Paths.get(args[0]).toAbsolutePath();
        String stylePath = args[1].replace("\\", "/");
        Path ctxJson = Paths.get(args[2]).toAbsolutePath();
        Path outputDir = Paths.get(args[3]).toAbsolutePath();

        String ctxText = new String(Files.readAllBytes(ctxJson), StandardCharsets.UTF_8);
        Map<String, Object> rootCtx = JSON.parseObject(ctxText, Map.class, JSONReader.Feature.UseBigDecimalForDoubles);
        // jeecg 官方模板（树表 Controller / Mapper.xml）依赖全局 Format 工具，这里补注入
        rootCtx.put("Format", new FormatTool());

        Configuration cfg = new Configuration(Configuration.VERSION_2_3_28);
        cfg.setNumberFormat("0.#####################");
        cfg.setDirectoryForTemplateLoading(templateRoot.toFile());
        cfg.setDefaultEncoding("UTF-8");
        cfg.setTemplateExceptionHandler(TemplateExceptionHandler.RETHROW_HANDLER);
        cfg.setNewBuiltinClassResolver(TemplateClassResolver.SAFER_RESOLVER);

        Path styleRoot = templateRoot.resolve(stylePath);
        if (!Files.isDirectory(styleRoot)) {
            throw new RuntimeException("stylePath not found: " + styleRoot);
        }

        Files.createDirectories(outputDir);
        List<String> generated = new ArrayList<>();

        // 官方约定：模板永远用 rootCtx 渲染一次。带 [1-n] 的模板内部用 <#list subTables as sub>
        // 自己迭代子表，并用 #segment#XXX 标记切分输出。FtlRunner 不再外层迭代子表。
        try (java.util.stream.Stream<Path> walk = Files.walk(styleRoot)) {
            List<Path> files = walk.filter(Files::isRegularFile).collect(Collectors.toList());
            for (Path tpl : files) {
                String relFromRoot = templateRoot.relativize(tpl).toString().replace("\\", "/");
                String relFromStyle = styleRoot.relativize(tpl).toString().replace("\\", "/");
                String outRel = expandPath(relFromStyle, rootCtx);
                Path outFile = outputDir.resolve(outRel);
                renderOne(cfg, relFromRoot, rootCtx, outFile, generated);
            }
        }

        for (String g : generated) System.out.println("WROTE " + g);
        System.out.println("DONE " + generated.size() + " files -> " + outputDir);
    }

    private static void renderOne(Configuration cfg, String tplRel, Map<String, Object> ctx, Path outFile, List<String> generated) throws Exception {
        Template t = cfg.getTemplate(tplRel, "UTF-8");
        StringWriter sw = new StringWriter();
        t.process(ctx, sw);
        String content = sw.toString();

        // 判断是否需要 #segment# 切分：
        // 官方触发条件是"渲染后文件名以 [1-n] 开头"。模板路径含 [1-n] 即此类。
        // 这种模板内必含 #segment# 行；切分完成后丢弃原文件名（[1-n]Foo.java 不应落盘）。
        boolean isSegmented = SUB_RE.matcher(outFile.toString()).find();
        if (isSegmented) {
            splitAndWriteSegments(content, outFile, generated);
        } else {
            Path finalOut = adjustOutputPath(outFile);
            Files.createDirectories(finalOut.getParent());
            Files.write(finalOut, content.getBytes(StandardCharsets.UTF_8));
            generated.add(finalOut.toString());
        }
    }

    /** 按 #segment#FILENAME 标记把内容切分成多个文件，全部写到 outFile 的父目录下。
     *  - 首个 #segment# 之前的内容（含空行/换行）一律丢弃；
     *  - 行末统一为 \r\n，UTF-8；
     *  - 没有任何 #segment# 行时不产生任何输出（与官方一致：[1-n] 模板必须自带切分标记）。
     */
    private static void splitAndWriteSegments(String content, Path outFile, List<String> generated) throws IOException {
        Path parent = adjustOutputPath(outFile).getParent();
        Files.createDirectories(parent);
        String[] lines = content.split("\\r?\\n", -1);
        Writer cur = null;
        Path curPath = null;
        try {
            for (String line : lines) {
                if (line.trim().length() > 0 && line.startsWith(SEGMENT_PREFIX)) {
                    if (cur != null) cur.close();
                    String segName = line.substring(SEGMENT_PREFIX.length()).trim();
                    curPath = parent.resolve(segName);
                    Files.createDirectories(curPath.getParent());
                    cur = Files.newBufferedWriter(curPath, StandardCharsets.UTF_8);
                    generated.add(curPath.toString());
                } else if (cur != null) {
                    cur.write(line);
                    cur.write("\r\n");
                }
                // 首个 segment 标记之前的内容直接丢弃
            }
        } finally {
            if (cur != null) cur.close();
        }
    }

    /** 把 .javai/.tsi/.vuei 还原成 .java/.ts/.vue（jeecg 模板约定的写法） */
    private static Path adjustOutputPath(Path p) {
        String name = p.getFileName().toString();
        String fixed = name;
        if (name.endsWith(".javai")) fixed = name.substring(0, name.length() - 6) + ".java";
        else if (name.endsWith(".vuei")) fixed = name.substring(0, name.length() - 5) + ".vue";
        else if (name.endsWith(".tsi"))  fixed = name.substring(0, name.length() - 4) + ".ts";
        return p.resolveSibling(fixed);
    }

    /** 把路径中的 ${var} 展开为 ctx 里的值。命名空间限定为顶层 string。 */
    private static String expandPath(String path, Map<String, Object> ctx) {
        Matcher m = VAR_RE.matcher(path);
        StringBuffer sb = new StringBuffer();
        while (m.find()) {
            String key = m.group(1);
            Object v = ctx.get(key);
            String s = (v == null) ? "" : v.toString();
            // bussiPackage 路径中通常是点号包；要换成斜线
            if ("bussiPackage".equals(key) || "entityPackage".equals(key) || "parentPackage".equals(key)) {
                s = s.replace('.', '/');
            }
            m.appendReplacement(sb, Matcher.quoteReplacement(s));
        }
        m.appendTail(sb);
        return sb.toString();
    }

    /** 对齐 jeecg 官方 org.jeecgframework.codegenerate.generate.util.SimpleFormat
     *  （模板里注入为变量 Format）。以下三个字符串转换方法按 codegenerate-1.5.6.jar
     *  字节码逐句复刻，确保与官方代码生成行为一致：
     *    - 已含目标分隔符则不再插入；
     *    - 末尾剥离前导分隔符（如 UserName -> user_name 而非 _user_name）。
     *  官方的 number/date/currency 等格式化方法当前模板未使用，未复刻。
     *  （null 入参官方会 NPE，这里返回 null 作为防御，不影响非 null 行为。） */
    public static class FormatTool {
        public String humpToUnderline(String para) {
            if (para == null) return null;
            StringBuilder sb = new StringBuilder(para);
            int offset = 0;
            if (!para.contains("_")) {
                for (int i = 0; i < para.length(); i++) {
                    if (Character.isUpperCase(para.charAt(i))) {
                        sb.insert(i + offset, "_");
                        offset++;
                    }
                }
            }
            String r = sb.toString().toLowerCase();
            return r.startsWith("_") ? r.substring(1) : r;
        }

        public String humpToShortbar(String para) {
            if (para == null) return null;
            StringBuilder sb = new StringBuilder(para);
            int offset = 0;
            if (!para.contains("-")) {
                for (int i = 0; i < para.length(); i++) {
                    if (Character.isUpperCase(para.charAt(i))) {
                        sb.insert(i + offset, "-");
                        offset++;
                    }
                }
            }
            String r = sb.toString().toLowerCase();
            return r.startsWith("-") ? r.substring(1) : r;
        }

        public String underlineToHump(String para) {
            if (para == null) return null;
            StringBuilder sb = new StringBuilder();
            for (String part : para.split("_")) {
                if (!para.contains("_")) {
                    sb.append(part);
                } else if (sb.length() == 0) {
                    sb.append(part.toLowerCase());
                } else if (part.length() > 0) {  // 官方未判空，此处加固避免空段越界
                    sb.append(part.substring(0, 1).toUpperCase());
                    sb.append(part.substring(1).toLowerCase());
                }
            }
            return sb.toString();
        }
    }
}
