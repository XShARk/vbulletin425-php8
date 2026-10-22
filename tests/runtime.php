<?php
// Synthetic tests for our own helper functions; no vendor code required.
$dir=sys_get_temp_dir().'/vb425-runtime-'.bin2hex(random_bytes(5));mkdir($dir,0700);
copy(__DIR__.'/../php/transformer.php',$dir.'/vb425_php8_transformer.php');
copy(__DIR__.'/../php/runtime.php',$dir.'/runtime.php');
try {
    require $dir.'/runtime.php';
    $checks=0;
    $check=function($condition) use (&$checks) { $checks++;if (!$condition) throw new RuntimeException('Check failed: '.$checks); };
    $a=['x'=>9,3=>null];
    $first=vb425_php8_each($a);$check($first['key']==='x' && $first['value']===9);
    $second=vb425_php8_each($a);$check($second['key']===3 && $second['value']===null);
    $check(vb425_php8_each($a)===false);
    $check(vb425_php8_count(null)===0 && vb425_php8_count(false)===1);
    $check(vb425_php8_count([1,[2]],COUNT_RECURSIVE)===3);
    $check(vb425_php8_implode([1,2],':')==='1:2');
    $check(vb425_php8_implode(':',[1,2])==='1:2');
    $check(vb425_php8_implode([1,2])==='12');
    $check(vb425_php8_number('12')===12 && vb425_php8_number('2.5')===2.5);
    $check(vb425_php8_number('oops')===0.0);
    $value=1;$fn=vb425_php8_closure('&$item','$item += 4;');$fn($value);$check($value===5);
    $check(vb425_php8_magic_quotes()===false);
    $fragment=vb425_php8_fragment('$a=array("item"=>8);return $a[item];');
    $check(eval($fragment)===8);
    echo json_encode(['checks'=>$checks,'passed'=>true]),PHP_EOL;
} finally {unlink($dir.'/runtime.php');unlink($dir.'/vb425_php8_transformer.php');rmdir($dir);}
