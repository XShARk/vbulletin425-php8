<?php
if (PHP_SAPI!=='cli') { http_response_code(403);exit; }
require __DIR__.'/transformer.php';
$request=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR);
$result=[];
foreach ($request as $row) {
    $before=base64_decode($row['source'],true);
    if ($before===false) throw new RuntimeException('Invalid base64 input');
    $after=vb425_php8_source($before);
    $error=null;
    try { token_get_all($after,TOKEN_PARSE); }
    catch (ParseError $e) { $error=['line'=>$e->getLine(),'kind'=>'parse_error']; }
    $result[]=['path'=>$row['path'],'source'=>base64_encode($after),'parse_error'=>$error];
}
echo json_encode($result,JSON_THROW_ON_ERROR);
